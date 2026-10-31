"""Portable HTTP integration test; uses a mock inference endpoint, not a real model/desktop."""
from __future__ import annotations
import http.server, json, os, signal, socket, subprocess, threading, time, urllib.request, urllib.error, uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class InferenceHandler(http.server.BaseHTTPRequestHandler):
    plan=None
    def log_message(self,*args): pass
    def do_GET(self):
        body=json.dumps({'data':[{'id':'mock-orbit'}]}).encode(); self.send_response(200); self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
    def do_POST(self):
        self.rfile.read(int(self.headers.get('Content-Length','0')))
        body=json.dumps({'choices':[{'message':{'content':json.dumps(self.plan)}}]}).encode(); self.send_response(200); self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)

def free_port():
    s=socket.socket(); s.bind(('127.0.0.1',0)); p=s.getsockname()[1]; s.close(); return p

def request(port,path,data=None,origin=None):
    headers={}
    if data is not None: headers['Content-Type']='application/json'
    if origin: headers['Origin']=origin
    raw=json.dumps(data).encode() if data is not None else None
    req=urllib.request.Request(f'http://127.0.0.1:{port}{path}',data=raw,headers=headers,method='POST' if data is not None else 'GET')
    try:
        with urllib.request.urlopen(req,timeout=5) as r: return r.status,json.load(r)
    except urllib.error.HTTPError as e: return e.code,json.load(e)

def start_app(port):
    env={**os.environ,'ORBIT_PORT':str(port),'PYTHONHOME':'','PYTHONPATH':''}
    p=subprocess.Popen([str(ROOT/'run_linux.sh')],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True)
    for _ in range(100):
        if p.poll() is not None: raise RuntimeError('Portable server exited: '+p.stderr.read())
        try:
            status,_=request(port,'/api/status')
            if status==200: return p
        except Exception: time.sleep(.1)
    raise RuntimeError('Portable server did not become ready')

def stop_app(p):
    if p.poll() is None:
        p.send_signal(signal.SIGINT)
        try:p.wait(timeout=10)
        except subprocess.TimeoutExpired:p.kill();p.wait(timeout=3)

def main():
    cfg=ROOT/'CONFIG/orbit.json'; original=cfg.read_bytes(); port=free_port(); model_port=free_port(); app=None; mock=None; task_id=None
    suffix=uuid.uuid4().hex[:8]; folder=f'.orbit-integration-{suffix}'; source=ROOT/'DATA/workspace'/f'.orbit-source-{suffix}.txt'; dest=f'{folder}/copied.txt'
    try:
        InferenceHandler.plan={'objective':'copy source into test folder','steps':[{'id':1,'action':'workspace.create_directory','description':'Create isolated folder','parameters':{'path':folder},'depends_on':[],'expected':'Folder exists'},{'id':2,'action':'workspace.copy_file','description':'Copy one source file','parameters':{'source':source.name,'destination':dest},'depends_on':[1],'expected':'Exact copy is present'}]}
        mock=http.server.ThreadingHTTPServer(('127.0.0.1',model_port),InferenceHandler); threading.Thread(target=mock.serve_forever,daemon=True).start()
        app=start_app(port)
        code,models=request(port,'/api/models'); assert code==200
        url=f'http://127.0.0.1:{model_port}/v1'
        code,m=request(port,'/api/models/config',{'role':'language','enabled':True,'model':'mock-orbit','base_url':url,'model_path':'','format':'mock-json','quantization':'none','backend':'mock local endpoint'}); assert code==200 and m['configured']
        (ROOT/'DATA/workspace').mkdir(parents=True,exist_ok=True); source.write_text('controlled integration payload',encoding='utf-8')
        code,task=request(port,'/api/tasks',{'objective':'Copy one file into a new folder.'}); assert code==201 and task['planning_source']=='local-model' and len(task['steps'])==2,task
        task_id=task['id']
        assert task['steps'][1]['permission']=='B'
        code,step=request(port,'/api/execute',{'task_id':task_id,'step_id':1}); assert code==200 and step['step']['verified']
        code,approval=request(port,'/api/execute',{'task_id':task_id,'step_id':2}); assert code==403 and approval['approval_required'] and not (ROOT/'DATA/workspace'/dest).exists()
        code,approved=request(port,'/api/approve',{'task_id':task_id,'step_id':2}); assert code==200 and approved['approved']
        code,step=request(port,'/api/execute',{'task_id':task_id,'step_id':2}); assert code==200 and step['step']['verified']
        assert (ROOT/'DATA/workspace'/dest).read_text(encoding='utf-8')=='controlled integration payload'
        with urllib.request.urlopen(f'http://127.0.0.1:{port}/',timeout=5) as page: assert page.status==200 and b'ORBIT' in page.read()
        code,_=request(port,'/api/execute',{'task_id':task_id,'step_id':2},origin='http://attacker.example'); assert code==403
        stop_app(app); app=None
        app=start_app(port)
        code,tasks=request(port,'/api/tasks'); saved=next(t for t in tasks if t['id']==task_id)
        assert saved['status']=='completed' and saved['planning_source']=='local-model' and all(x['status']=='done' for x in saved['steps'])
        code,result=request(port,'/api/execute',{'task_id':task_id,'step_id':2}); assert code==200 and result['already_done'] is True
        print('PASS (mock inference; no real model or GUI): bundled Linux launcher; dashboard/status; model-role config/probe; 2-step model plan; registry/dependency validation; B action waits for exact approval; copied file verified; cross-origin write denied; model provenance and completed task persist after process restart; completed step not repeated.')
    finally:
        if app: stop_app(app)
        if mock: mock.shutdown();mock.server_close()
        cfg.write_bytes(original)
        source.unlink(missing_ok=True); (ROOT/'DATA/workspace'/dest).unlink(missing_ok=True); (ROOT/'DATA/workspace'/folder).rmdir() if (ROOT/'DATA/workspace'/folder).is_dir() else None
        if task_id:
            # Erase only this test's task record after the process is closed.
            from sys import path
            path.insert(0,str(ROOT))
            from orbit.memory import MemoryStore
            store=MemoryStore(ROOT/'DATA/orbit.sqlite3')
            try: store.delete_task(task_id)
            finally: store.close()

if __name__=='__main__':main()
