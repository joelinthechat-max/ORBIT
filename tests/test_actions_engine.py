import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from orbit.actions import ActionRegistry
from orbit.engine import TaskEngine
from orbit.memory import MemoryStore
from orbit.planner import Planner

class Config:
 def __call__(self): return {'security':{'action_permissions':{'A':True,'B':True,'C':True,'D':False}}}

class ActionsEngineTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name); self.workspace=self.root/'workspace'; self.workspace.mkdir(); self.mem=MemoryStore(self.root/'memory.db'); self.registry=ActionRegistry(self.workspace); self.engine=TaskEngine(self.mem,self.registry,Planner(),Config())
 def tearDown(self): self.mem.close(); self.tmp.cleanup()
 def task(self,steps,objective='test objective'):
  t={'id':'t1','objective':objective,'created':1,'status':'planned','steps':steps,'outcome':''}; self.mem.save_task(t); return t
 def step(self,n,action,params,permission='A',deps=None):
  m=self.registry.validate(action,params); return {'id':n,'kind':'registered','action':action,'title':action,'parameters':params,'permission':permission,'depends_on':deps or [],'expected':'verified','status':'pending','approval':None,'reversible':m['reversible'],'consequence':m['consequence']}
 def test_rejects_unknown_action_bad_parameters_and_path_escape(self):
  with self.assertRaises(ValueError): self.registry.validate('shell.exec',{'command':'touch pwned'})
  with self.assertRaises(ValueError): self.registry.validate('workspace.create_file',{'path':'a.txt','content':'x','extra':True})
  with self.assertRaises(ValueError): self.registry.validate('workspace.create_file',{'path':'../outside.txt','content':'x'})
  with self.assertRaises(ValueError): self.registry.validate('workspace.read_file',{'path':'C:/secret.txt'})
 def test_create_directory_file_and_verify_multistep(self):
  steps=[self.step(1,'workspace.create_directory',{'path':'ORBIT Test'}),self.step(2,'workspace.create_file',{'path':'ORBIT Test/report.txt','content':'renewables' },deps=[1]),self.step(3,'workspace.verify_file',{'path':'ORBIT Test/report.txt','expected_content':'renewables'},deps=[2])]
  t=self.task(steps)
  with self.assertRaises(RuntimeError): self.engine.execute('t1',2)
  for i in (1,2,3): self.assertEqual(self.engine.execute('t1',i)['step']['status'],'done')
  self.assertEqual(self.mem.get_task('t1')['status'],'completed')
  self.assertTrue((self.workspace/'ORBIT Test/report.txt').is_file())
  self.assertTrue(self.engine.execute('t1',2)['already_done'])
 def test_overwrite_refused_without_approval_capability(self):
  (self.workspace/'a.txt').write_text('original')
  s=self.step(1,'workspace.create_file',{'path':'a.txt','content':'new'})
  self.task([s])
  with self.assertRaises(RuntimeError): self.engine.execute('t1',1)
  self.assertEqual((self.workspace/'a.txt').read_text(),'original')
 def test_class_b_exact_parameter_approval_and_copy(self):
  (self.workspace/'a.txt').write_text('copy me')
  self.task([self.step(1,'workspace.copy_file',{'source':'a.txt','destination':'b.txt'},'B')])
  r=self.engine.execute('t1',1); self.assertTrue(r['approval_required']); self.assertFalse((self.workspace/'b.txt').exists())
  self.engine.approve('t1',1)
  step=self.mem.get_task('t1')['steps'][0]; step['parameters']['destination']='c.txt'; t=self.mem.get_task('t1'); t['steps'][0]=step; self.mem.save_task(t)
  self.assertTrue(self.engine.execute('t1',1)['approval_required'])
  self.assertFalse((self.workspace/'c.txt').exists())
 def test_class_c_delete_needs_specific_approval(self):
  (self.workspace/'erase.txt').write_text('data')
  self.task([self.step(1,'workspace.delete_file',{'path':'erase.txt'},'C')])
  self.assertTrue(self.engine.execute('t1',1)['approval_required']); self.assertTrue((self.workspace/'erase.txt').exists())
  self.engine.approve('t1',1); self.engine.execute('t1',1); self.assertFalse((self.workspace/'erase.txt').exists())
 def test_deterministic_acceptance_objective_creates_folder_file_verify(self):
  t=self.engine.create_task('Create a folder named ORBIT Test inside my workspace, create a text file called report.txt, write a short report about renewable energy in it, and verify that the file was saved correctly.')
  self.assertEqual([x['action'] for x in t['steps']],['workspace.create_directory','workspace.create_file','workspace.verify_file'])
  for s in t['steps']: self.engine.execute(t['id'],s['id'])
  self.assertEqual(self.mem.get_task(t['id'])['status'],'completed')
  self.assertIn('Renewable energy',(self.workspace/'ORBIT Test/report.txt').read_text())
 def test_migrates_legacy_file_task_and_keeps_completed_write_done(self):
  target=self.workspace/'old.txt'; target.write_text('already stored')
  self.task([{'id':1,'kind':'file_write','title':'Create old file','detail':'old.txt\nalready stored','status':'done','result':'Old version write verified'},{'id':2,'kind':'verify','title':'Verify old file','detail':'','status':'pending'}],objective='old task')
  self.assertEqual(self.engine.migrate_legacy_tasks(),1)
  task=self.mem.get_task('t1'); self.assertEqual(task['steps'][0]['action'],'workspace.create_file'); self.assertEqual(task['steps'][0]['status'],'done')
  self.assertEqual(task['steps'][1]['action'],'workspace.verify_file'); self.engine.execute('t1',2)
  self.assertEqual(target.read_text(),'already stored'); self.assertEqual(self.mem.get_task('t1')['status'],'completed')
 def test_unsupported_legacy_file_format_is_paused_for_review(self):
  self.task([{'id':1,'kind':'file_write','title':'Create PDF','detail':'report.pdf\ntext','status':'pending'}])
  self.engine.migrate_legacy_tasks(); task=self.mem.get_task('t1')
  self.assertEqual(task['status'],'paused'); self.assertEqual(task['steps'][0]['kind'],'legacy_needs_review'); self.assertEqual(task['steps'][0]['status'],'failed')

if __name__=='__main__':unittest.main()
