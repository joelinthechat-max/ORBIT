"""Portable SQLite memory with migration, integrity checks, bounded retrieval and backups."""
from __future__ import annotations
import json, sqlite3, time, shutil
from pathlib import Path
from typing import Any
from threading import RLock
from functools import wraps
import uuid

SCHEMA_VERSION=2
def _synchronized(method):
    @wraps(method)
    def wrapped(self,*args,**kwargs):
        with self._lock: return method(self,*args,**kwargs)
    return wrapped

class MemoryStore:
    def __init__(self, path: Path):
        self._lock=RLock()
        self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(str(self.path),timeout=10,check_same_thread=False)
        self.db.row_factory=sqlite3.Row
        try:
            self.db.execute("PRAGMA journal_mode=WAL"); self.db.execute("PRAGMA foreign_keys=ON")
            self._migrate()
        except sqlite3.DatabaseError:
            # Preserve the damaged database for manual recovery instead of silently overwriting it.
            self.db.close(); stamp=time.strftime('%Y%m%d-%H%M%S')
            damaged=self.path.with_name(self.path.name+'.corrupt-'+stamp)
            self.path.replace(damaged)
            for suffix in ('-wal','-shm'):
                side=Path(str(self.path)+suffix)
                if side.exists(): side.replace(Path(str(damaged)+suffix))
            self.db=sqlite3.connect(str(self.path),timeout=10,check_same_thread=False); self.db.row_factory=sqlite3.Row
            self.db.execute('PRAGMA journal_mode=WAL'); self.db.execute('PRAGMA foreign_keys=ON'); self._migrate()
    def _migrate(self):
        with self.db:
            self.db.execute("CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY,value TEXT NOT NULL)")
            row=self.db.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()
            version=int(row['value']) if row else 0
            if version>SCHEMA_VERSION: raise RuntimeError(f"Memory DB schema {version} is newer than supported {SCHEMA_VERSION}")
            if version<1:
                self.db.executescript("""
                CREATE TABLE tasks(id TEXT PRIMARY KEY, objective TEXT NOT NULL, created REAL NOT NULL, updated REAL NOT NULL, status TEXT NOT NULL, steps_json TEXT NOT NULL, outcome TEXT NOT NULL DEFAULT '');
                CREATE INDEX tasks_created_idx ON tasks(created DESC);
                CREATE TABLE preferences(key TEXT PRIMARY KEY,value TEXT NOT NULL,approved_at REAL NOT NULL);
                CREATE TABLE knowledge(id INTEGER PRIMARY KEY,kind TEXT NOT NULL,title TEXT NOT NULL,body TEXT NOT NULL,created REAL NOT NULL);
                CREATE INDEX knowledge_search_idx ON knowledge(title,body);
                INSERT OR REPLACE INTO metadata(key,value) VALUES('schema_version','1');
                """)
            if version<2:
                cols={r[1] for r in self.db.execute('PRAGMA table_info(tasks)')}
                if 'metadata_json' not in cols: self.db.execute("ALTER TABLE tasks ADD COLUMN metadata_json TEXT NOT NULL DEFAULT '{}'")
                self.db.execute("INSERT OR REPLACE INTO metadata(key,value) VALUES('schema_version','2')")
    def integrity_check(self):
        return [r[0] for r in self.db.execute('PRAGMA integrity_check')]
    def save_task(self,t:dict):
        now=time.time(); payload=json.dumps(t.get('steps',[]),ensure_ascii=False); metadata=json.dumps({k:t[k] for k in ('planning_source','planning_error','initial_plan','current_plan','latest_observation','latest_assessment','revised_plan_proposal','observation_history','execution_trace','final_verification','current_phase') if k in t},ensure_ascii=False)
        with self.db:
            self.db.execute("INSERT INTO tasks(id,objective,created,updated,status,steps_json,outcome,metadata_json) VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET updated=excluded.updated,status=excluded.status,steps_json=excluded.steps_json,outcome=excluded.outcome,metadata_json=excluded.metadata_json",(t['id'],t['objective'],t.get('created',now),now,t.get('status','planned'),payload,t.get('outcome',''),metadata))
    def _task(self,row):
        try: steps=json.loads(row['steps_json']);
        except (json.JSONDecodeError,TypeError): steps=[]
        try: metadata=json.loads(row['metadata_json'])
        except (KeyError,TypeError,ValueError): metadata={}
        return {'id':row['id'],'objective':row['objective'],'created':row['created'],'updated':row['updated'],'status':row['status'],'steps':steps,'outcome':row['outcome'],**{k:metadata[k] for k in ('planning_source','planning_error','initial_plan','current_plan','latest_observation','latest_assessment','revised_plan_proposal','observation_history','execution_trace','final_verification','current_phase') if k in metadata}}
    def get_task(self,tid):
        row=self.db.execute('SELECT * FROM tasks WHERE id=?',(tid,)).fetchone(); return self._task(row) if row else None
    def list_tasks(self,limit=100):
        return [self._task(r) for r in self.db.execute('SELECT * FROM tasks ORDER BY created DESC LIMIT ?',(max(1,min(int(limit),500)),))]
    def search_tasks(self,q,limit=50):
        q=q.strip()
        if not q: return self.list_tasks(limit)
        return [self._task(r) for r in self.db.execute("SELECT * FROM tasks WHERE objective LIKE ? OR outcome LIKE ? ORDER BY created DESC LIMIT ?",(f'%{q}%',f'%{q}%',max(1,min(int(limit),200))))]
    def set_preference(self,key,value,approved=False):
        if not approved: raise PermissionError('Saving a user preference requires explicit approval')
        with self.db: self.db.execute('INSERT INTO preferences VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value,approved_at=excluded.approved_at',(key,json.dumps(value,ensure_ascii=False),time.time()))
    def preferences(self):
        out=[]
        for r in self.db.execute('SELECT * FROM preferences ORDER BY key'):
            try: val=json.loads(r['value'])
            except Exception: val='[corrupt value]'
            out.append({'key':r['key'],'value':val,'approved_at':r['approved_at']})
        return out
    def delete_preference(self,key):
        with self.db: return self.db.execute('DELETE FROM preferences WHERE key=?',(key,)).rowcount
    def add_knowledge(self,kind,title,body,approved=False):
        if not approved: raise PermissionError('Saving knowledge requires explicit approval')
        with self.db: cur=self.db.execute('INSERT INTO knowledge(kind,title,body,created) VALUES(?,?,?,?)',(kind,title,body,time.time())); return cur.lastrowid
    def search_memory(self,q,limit=20):
        q=q.strip(); lim=max(1,min(int(limit),100))
        tasks=self.search_tasks(q,lim) if q else self.list_tasks(lim)
        if not q: rows=self.db.execute('SELECT * FROM knowledge ORDER BY created DESC LIMIT ?',(lim,)).fetchall()
        else: rows=self.db.execute('SELECT * FROM knowledge WHERE title LIKE ? OR body LIKE ? ORDER BY created DESC LIMIT ?',(f'%{q}%',f'%{q}%',lim)).fetchall()
        return {'tasks':tasks,'knowledge':[dict(r) for r in rows]}
    def delete_task(self,tid):
        with self.db: return self.db.execute('DELETE FROM tasks WHERE id=?',(tid,)).rowcount
    def delete_knowledge(self,row_id):
        with self.db: return self.db.execute('DELETE FROM knowledge WHERE id=?',(int(row_id),)).rowcount
    def backup(self,target:Path):
        target=Path(target); target.parent.mkdir(parents=True,exist_ok=True)
        self.db.execute('PRAGMA wal_checkpoint(FULL)')
        dest=sqlite3.connect(str(target))
        try: self.db.backup(dest)
        finally: dest.close()
        return target
    def restore(self,source:Path):
        source=Path(source)
        check=sqlite3.connect(f'file:{source.resolve()}?mode=ro',uri=True)
        try:
            result=[r[0] for r in check.execute('PRAGMA integrity_check')]
            if result!=['ok']: raise ValueError('Backup integrity check failed')
            v=check.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()
            if not v or int(v[0]) not in {1,SCHEMA_VERSION}: raise ValueError('Unsupported backup schema')
            source_version=int(v[0])
            # Validate required tables before touching current data.
            tables={r[0] for r in check.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if not {'tasks','preferences','knowledge','metadata'}<=tables: raise ValueError('Backup missing required tables')
            staging=self.path.with_name(self.path.name+f'.restore-{uuid.uuid4().hex}.tmp')
            out=sqlite3.connect(str(staging))
            try: check.backup(out)
            finally: out.close()
        finally: check.close()
        if source_version<SCHEMA_VERSION:
            migrated=MemoryStore(staging); migrated.close()
        # Close, replace atomically, reopen, restore constraints/pragmas.
        self.db.close(); staging.replace(self.path)
        for suffix in ('-wal','-shm'): Path(str(staging)+suffix).unlink(missing_ok=True)
        self.db=sqlite3.connect(str(self.path),timeout=10,check_same_thread=False); self.db.row_factory=sqlite3.Row
        self.db.execute('PRAGMA journal_mode=WAL'); self.db.execute('PRAGMA foreign_keys=ON')
        return self.integrity_check()
    def recoverable_tasks(self):
        return [t for t in self.list_tasks(500) if t['status'] in {'planned','running','paused','failed','observing','awaiting_review'} and any(s.get('status')!='done' for s in t['steps'])]
    def recover_running_tasks(self):
        """Requeue only known idempotent file workflow actions after process interruption."""
        recovered=0
        for task in self.list_tasks(500):
            if task.get('status') in {'observing','awaiting_review'} and any(s.get('status')=='awaiting_observation' for s in task.get('steps',[])):
                task['status']='paused'; task['current_phase']='recovery_review'; task.pop('latest_observation',None)
                task.setdefault('execution_trace',[]).append({'at':time.time(),'phase':'restart_recovery','note':'External action may have occurred; its result will not be replayed. Capture a fresh screenshot and review before confirming.'})
                task['execution_trace']=task['execution_trace'][-100:]; self.save_task(task); recovered+=1; continue
            if task['status']!='running': continue
            safe=True
            for step in task['steps']:
                if step.get('status')=='running':
                    if step.get('kind') in {'file_write','verify'} or (step.get('kind')=='registered' and step.get('permission')=='A' and step.get('action') in {'workspace.list','workspace.search','workspace.read_file','workspace.verify_file','workspace.create_directory','workspace.create_file'}):
                        step['status']='pending'; step['result']='Recovered after restart; action will be checked before any write.'
                    else:
                        safe=False; step['status']='interrupted_review'; step['approval']=None
                        step['result']='Interrupted during an action that ORBIT will not automatically repeat. Inspect the affected file/system state and create a revised task.'
            task['status']='planned' if safe else 'paused'
            self.save_task(task); recovered+=1
        return recovered
    def prune_tasks(self,retention_days=None):
        if retention_days is None: return 0
        days=max(1,int(retention_days)); cutoff=time.time()-days*86400
        with self.db: return self.db.execute('DELETE FROM tasks WHERE created<?',(cutoff,)).rowcount
    def close(self): self.db.close()

# ThreadingHTTPServer can issue parallel requests; protect its single shared connection.
for _name in ('integrity_check','save_task','get_task','list_tasks','search_tasks','set_preference','preferences','delete_preference','add_knowledge','search_memory','delete_task','delete_knowledge','backup','restore','recoverable_tasks','recover_running_tasks','prune_tasks','close'):
    setattr(MemoryStore,_name,_synchronized(getattr(MemoryStore,_name)))
