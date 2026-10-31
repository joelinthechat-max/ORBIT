import json, sqlite3, sys, tempfile, unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from orbit.memory import MemoryStore
from orbit.adapters.models import validate_observation

class MemoryTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name); self.db=self.root/'memory.sqlite3'; self.mem=MemoryStore(self.db)
 def tearDown(self): self.mem.close(); self.tmp.cleanup()
 def test_task_survives_store_restart_and_resume(self):
  task={'id':'abc','objective':'persist','created':123.0,'status':'running','steps':[{'id':1,'kind':'file_write','status':'done'},{'id':2,'kind':'verify','status':'pending'}]}
  self.mem.save_task(task); self.mem.close(); self.mem=MemoryStore(self.db)
  recovered=self.mem.recoverable_tasks(); self.assertEqual(len(recovered),1); self.assertEqual(recovered[0]['steps'][0]['status'],'done'); self.assertEqual(recovered[0]['steps'][1]['status'],'pending')
 def test_running_file_step_is_safely_requeued(self):
  self.mem.save_task({'id':'crash','objective':'interrupted','created':123,'status':'running','steps':[{'id':1,'kind':'file_write','status':'done'},{'id':2,'kind':'verify','status':'running'}]})
  self.assertEqual(self.mem.recover_running_tasks(),1)
  task=self.mem.get_task('crash'); self.assertEqual(task['steps'][0]['status'],'done'); self.assertEqual(task['steps'][1]['status'],'pending'); self.assertEqual(task['status'],'planned')
 def test_interrupted_high_risk_action_pauses_without_requeue(self):
  self.mem.save_task({'id':'risk','objective':'move','created':123,'status':'running','steps':[{'id':1,'kind':'registered','action':'workspace.move_file','permission':'B','status':'running','parameters':{'source':'a','destination':'b'},'approval':{'token':'old'}}]})
  self.mem.recover_running_tasks(); task=self.mem.get_task('risk')
  self.assertEqual(task['status'],'paused'); self.assertEqual(task['steps'][0]['status'],'interrupted_review'); self.assertIsNone(task['steps'][0]['approval'])
 def test_interrupted_observation_requires_fresh_review_not_replay(self):
  self.mem.save_task({'id':'observe','objective':'desktop action','created':123,'status':'awaiting_review','steps':[{'id':1,'kind':'registered','action':'desktop.type_text','permission':'B','status':'awaiting_observation','parameters':{'text':'hello'},'approval':None}],'latest_observation':{'observed_at':123,'screen_description':'stale'}})
  self.assertEqual(self.mem.recover_running_tasks(),1);task=self.mem.get_task('observe')
  self.assertEqual(task['status'],'paused');self.assertEqual(task['steps'][0]['status'],'awaiting_observation');self.assertNotIn('latest_observation',task)
 def test_preference_needs_explicit_approval(self):
  with self.assertRaises(PermissionError): self.mem.set_preference('theme','dark')
  self.mem.set_preference('theme','dark',approved=True); self.assertEqual(self.mem.preferences()[0]['value'],'dark')
 def test_backup_restore_integrity(self):
  self.mem.save_task({'id':'before','objective':'before','created':1,'status':'completed','steps':[]})
  backup=self.root/'backup.sqlite3'; self.mem.backup(backup); self.mem.save_task({'id':'after','objective':'after','created':2,'status':'completed','steps':[]})
  self.assertEqual(self.mem.restore(backup),['ok']); self.assertIsNotNone(self.mem.get_task('before')); self.assertIsNone(self.mem.get_task('after'))
 def test_old_schema_backup_migrates_on_restore(self):
  old=self.root/'old-v1.sqlite3'; db=sqlite3.connect(old)
  db.executescript("CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL); CREATE TABLE tasks(id TEXT PRIMARY KEY,objective TEXT NOT NULL,created REAL NOT NULL,updated REAL NOT NULL,status TEXT NOT NULL,steps_json TEXT NOT NULL,outcome TEXT NOT NULL DEFAULT ''); CREATE TABLE preferences(key TEXT PRIMARY KEY,value TEXT NOT NULL,approved_at REAL NOT NULL); CREATE TABLE knowledge(id INTEGER PRIMARY KEY,kind TEXT NOT NULL,title TEXT NOT NULL,body TEXT NOT NULL,created REAL NOT NULL); INSERT INTO metadata VALUES('schema_version','1');")
  db.execute("INSERT INTO tasks VALUES('old','from old backup',1,1,'completed','[]','')"); db.commit(); db.close()
  self.assertEqual(self.mem.restore(old),['ok']); self.assertEqual(self.mem.get_task('old')['objective'],'from old backup')
 def test_plan_source_metadata_survives_restart(self):
  self.mem.save_task({'id':'model','objective':'plan','created':1,'status':'planned','steps':[],'planning_source':'local-model','planning_error':'fallback note'})
  self.mem.close(); self.mem=MemoryStore(self.db); row=self.mem.get_task('model')
  self.assertEqual(row['planning_source'],'local-model'); self.assertEqual(row['planning_error'],'fallback note')
 def test_advisory_and_revised_plan_metadata_survive_restart_without_authorization(self):
  advisory={'status':'advisory','assessment':'likely_success','confidence':0.8,'verified_by_model':False}
  proposal={'steps':[{'id':1,'action':'workspace.read_file','status':'pending'}],'execution_authorized':False,'auto_execute':False}
  self.mem.save_task({'id':'adaptive','objective':'resume safely','created':1,'status':'failed','steps':[{'id':1,'action':'desktop.click','status':'failed','verified':False}],'latest_assessment':advisory,'revised_plan_proposal':proposal})
  self.mem.close(); self.mem=MemoryStore(self.db); row=self.mem.get_task('adaptive')
  self.assertEqual(row['latest_assessment'],advisory); self.assertEqual(row['revised_plan_proposal'],proposal)
  self.assertEqual(row['steps'][0]['status'],'failed'); self.assertFalse(row['steps'][0]['verified'])
 def test_search_is_bounded_and_relevant(self):
  self.mem.save_task({'id':'x','objective':'Plan alpha','created':1,'status':'done','steps':[]})
  self.assertEqual(self.mem.search_tasks('alpha')[0]['id'],'x'); self.assertEqual(len(self.mem.search_tasks('')),1)
 def test_knowledge_requires_approval_and_can_be_removed(self):
  with self.assertRaises(PermissionError): self.mem.add_knowledge('procedure','alpha','body')
  row=self.mem.add_knowledge('procedure','alpha','body',approved=True)
  self.assertEqual(self.mem.search_memory('alpha')['knowledge'][0]['id'],row)
  self.assertEqual(self.mem.delete_knowledge(row),1)
 def test_concurrent_task_writes_are_serialized(self):
  def save(i): self.mem.save_task({'id':str(i),'objective':f'task {i}','created':i+1,'status':'planned','steps':[]})
  with ThreadPoolExecutor(max_workers=8) as pool: list(pool.map(save,range(32)))
  self.assertEqual(len(self.mem.list_tasks(100)),32)
 def test_corrupted_store_is_quarantined(self):
  self.mem.close(); self.db.write_bytes(b'not sqlite db')
  store=MemoryStore(self.db)
  try:
   self.assertEqual(store.integrity_check(),['ok']); self.assertTrue(list(self.root.glob('memory.sqlite3.corrupt-*')))
  finally: store.close(); self.mem=MemoryStore(self.db)

class VisionSchemaTests(unittest.TestCase):
 def test_validates_coordinates_and_scales(self):
  d={'screen_description':'dialog','elements':[{'type':'button','label':'OK','x':20,'y':10,'confidence':.9}]}
  out=validate_observation(d,100,50,200,100); self.assertEqual((out['elements'][0]['screen_x'],out['elements'][0]['screen_y']),(40,20))
 def test_rejects_out_of_bounds(self):
  with self.assertRaises(ValueError): validate_observation({'elements':[{'x':101,'y':0,'confidence':.9}]},100,50)
 def test_maps_resized_crop_coordinates_back_to_screen(self):
  d={'elements':[{'type':'button','label':'OK','x':50,'y':25,'confidence':.9}]}
  out=validate_observation(d,100,50,1000,800,100,200,200,100)
  self.assertEqual((out['elements'][0]['screen_x'],out['elements'][0]['screen_y']),(200,250))
  self.assertEqual(out['screen_origin'],{'x':100,'y':200})
 def test_rejects_malformed_potential_errors(self):
  with self.assertRaises(ValueError): validate_observation({'elements':[],'potential_errors':'not-a-list'},100,50)

if __name__=='__main__': unittest.main()
