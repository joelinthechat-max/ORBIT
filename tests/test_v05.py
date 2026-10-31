import json,os,sys,tempfile,time,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from orbit.actions import ActionRegistry
from orbit.adapters.browser import BrowserAdapter
from orbit.adapters.computer import DesktopAdapter,EMERGENCY_STOP
from orbit.adapters.llama_server import LocalModelManager
from orbit.engine import TaskEngine
from orbit.memory import MemoryStore
from orbit.planner import Planner
from orbit.resources import ResourceMonitor

class V05Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name); (self.root/'DATA').mkdir(); (self.root/'MODELS').mkdir(); (self.root/'RUNTIME/LINUX').mkdir(parents=True); self.workspace=self.root/'DATA/workspace'; self.workspace.mkdir(); self.cfg={'security':{'action_permissions':{'A':True,'B':True,'C':True,'D':False},'autonomous_mode_enabled':False,'computer_control_enabled':False,'approved_applications':{}},'browser':{'enabled':False,'headless':True,'executable_path':''},'autonomy':{'max_actions':4,'max_retries':0,'task_timeout_seconds':10},'models':{}}
  self.browser=BrowserAdapter(self.root,lambda:self.cfg); self.desktop=DesktopAdapter(); self.registry=ActionRegistry(self.workspace,self.desktop,self.browser,lambda:self.cfg,self.root/'DATA/screenshots'); self.memory=MemoryStore(self.root/'db.sqlite3'); self.engine=TaskEngine(self.memory,self.registry,Planner(),lambda:self.cfg)
 def tearDown(self):
  try:self.browser.close()
  except Exception:pass
  EMERGENCY_STOP.clear(); self.memory.close(); self.tmp.cleanup()
 def test_catalog_has_browser_and_desktop_with_fail_closed_risks(self):
  c={x['id']:x for x in self.registry.catalog()}
  self.assertEqual(c['browser.read_page']['permission'],'A'); self.assertEqual(c['browser.click']['permission'],'C'); self.assertEqual(c['browser.submit_form']['permission'],'C'); self.assertEqual(c['desktop.click']['permission'],'C'); self.assertEqual(c['desktop.clipboard_read']['permission'],'C')
  with self.assertRaises(ValueError):self.registry.validate('not.registered',{})
 def test_browser_url_and_selector_safety(self):
  with self.assertRaises(ValueError):self.browser._safe_url('file:///etc/passwd')
  class Request: pass
  class Route:
   def __init__(self,url): self.request=Request();self.request.url=url;self.result=None
   def abort(self,*args):self.result='abort'
   def continue_(self):self.result='continue'
  for url in ('file:///etc/passwd','chrome://settings','http://127.0.0.1:8765/private'):
   route=Route(url);self.browser._route_policy(route);self.assertEqual(route.result,'abort')
  route=Route('https://example.com/');self.browser._route_policy(route);self.assertEqual(route.result,'continue')
  with self.assertRaises(ValueError):self.browser.navigate('https://user:secret@example.com/')
  with self.assertRaises(ValueError):self.registry.validate('browser.navigate',{'url':'javascript:alert(1)'})
  with self.assertRaises(PermissionError):self.browser.navigate('https://example.org')
  with self.assertRaises(ValueError):self.registry.validate('browser.press',{'selector':'button','key':'Alt+F4'})
 def test_browser_submit_requires_confirmation_parameter_and_class_c(self):
  meta=self.registry.validate('browser.submit_form',{'selector':'form#profile','expected_confirmation':'Saved'})
  self.assertEqual(meta['permission'],'C')
  with self.assertRaises(ValueError):self.registry.validate('browser.submit_form',{'selector':'form#profile','expected_confirmation':''})
 def test_desktop_inputs_fail_closed_before_configuration_or_fresh_observation(self):
  params={'x':10,'y':10,'observed_at':time.time(),'button':'left','clicks':1}
  self.registry.validate('desktop.click',params)
  with self.assertRaises(PermissionError):self.registry.execute('desktop.click',params)
  self.cfg['security']['computer_control_enabled']=True
  with self.assertRaises(Exception):self.registry.execute('desktop.click',params)
  with self.assertRaises(ValueError):self.registry.validate('desktop.hotkey',{'keys':['alt','f4']})
  with self.assertRaises(ValueError):self.registry.validate('desktop.press_key',{'key':'Delete'})
 def test_application_launch_requires_exact_allowlist_and_uses_one_executable(self):
  if os.name=='nt': self.skipTest('Linux executable fixture')
  exe=Path('/usr/bin/true')
  if not exe.is_file(): self.skipTest('no harmless true executable')
  d=DesktopAdapter.__new__(DesktopAdapter); d._need=lambda:None
  with self.assertRaises(PermissionError):d.launch_application('not-listed',{})
  result=d.launch_application('true',{'true':str(exe)});self.assertGreater(result['pid'],0);self.assertIn('true',result['summary'])
 def test_approval_for_browser_click_is_parameter_bound(self):
  t={'id':'bb','objective':'test','created':time.time(),'status':'planned','steps':[{'id':1,'kind':'registered','action':'browser.click','title':'click exact search','parameters':{'selector':'role:button:Search'},'permission':'C','depends_on':[],'expected':'search page visible','status':'pending','approval':None}]}; self.memory.save_task(t)
  self.assertTrue(self.engine.execute('bb',1)['approval_required']); self.engine.approve('bb',1); task=self.memory.get_task('bb'); task['steps'][0]['parameters']['selector']='button.delete'; self.memory.save_task(task); self.assertTrue(self.engine.execute('bb',1)['approval_required'])
 def test_bounded_autonomy_opt_in_and_class_a_only(self):
  t=self.engine.create_task('Create a folder named Demo inside my workspace, create a text file called test.txt, write a short report about renewable energy in it, and verify that the file was saved correctly.')
  with self.assertRaises(PermissionError):self.engine.run_autonomous(t['id'])
  self.cfg['security']['autonomous_mode_enabled']=True
  r=self.engine.run_autonomous(t['id'],max_actions=3,task_timeout=10)
  self.assertEqual(r['status'],'completed'); self.assertEqual(r['actions'],3); self.assertTrue((self.workspace/'Demo/test.txt').is_file())
 def test_desktop_input_is_sent_not_verified_until_fresh_review(self):
  class FakeDesktop:
   def type_text(self,text): self.text=text
  self.cfg['security']['computer_control_enabled']=True
  registry=ActionRegistry(self.workspace,FakeDesktop(),None,lambda:self.cfg,self.root/'DATA/screenshots')
  engine=TaskEngine(self.memory,registry,Planner(),lambda:self.cfg)
  meta=registry.validate('desktop.type_text',{'text':'hello'})
  step={'id':1,'kind':'registered','action':'desktop.type_text','title':'Type hello','parameters':{'text':'hello'},'permission':'B','depends_on':[],'expected':'The target field visibly contains hello','status':'pending','approval':None,'reversible':False,'consequence':meta['consequence']}
  self.memory.save_task({'id':'observe','objective':'type hello','created':time.time(),'status':'planned','steps':[step]})
  self.assertTrue(engine.execute('observe',1)['approval_required']);engine.approve('observe',1)
  sent=engine.execute('observe',1);self.assertTrue(sent['awaiting_observation']);self.assertFalse(sent['step']['verified']);self.assertEqual(sent['step']['status'],'awaiting_observation')
  task=self.memory.get_task('observe');self.assertEqual(task['status'],'observing')
  with self.assertRaises(ValueError):engine.confirm_observation('observe',1,True)
  observed=engine.record_observation('observe',{'observed_at':time.time(),'screen_description':'Focused editor contains hello','elements':[]},'DATA/screenshots/latest.png')
  self.assertEqual(observed['status'],'awaiting_review');self.assertFalse(observed['steps'][0]['verified'])
  verified=engine.confirm_observation('observe',1,True)
  self.assertEqual(verified['status'],'completed');self.assertEqual(verified['final_verification']['source'],'user_observation')
  self.memory.close();self.memory=MemoryStore(self.root/'db.sqlite3')
  restored=self.memory.get_task('observe');self.assertTrue(restored['final_verification']['verified']);self.assertEqual(restored['execution_trace'][-1]['phase'],'user_verified')
 def test_class_b_autonomy_pauses_for_approval(self):
  (self.workspace/'a.txt').write_text('one')
  t={'id':'cb','objective':'copy','created':time.time(),'status':'planned','steps':[{'id':1,'kind':'registered','action':'workspace.copy_file','title':'copy','parameters':{'source':'a.txt','destination':'b.txt'},'permission':'B','depends_on':[],'expected':'copy','status':'pending','approval':None}]}; self.memory.save_task(t); self.cfg['security']['autonomous_mode_enabled']=True
  r=self.engine.run_autonomous('cb'); self.assertEqual(r['status'],'awaiting_approval'); self.assertFalse((self.workspace/'b.txt').exists())
 def test_resource_report_has_real_values_or_null(self):
  d=ResourceMonitor().sample(); self.assertIn('application_rss_mb',d); self.assertIsNone(d['model_server_rss_mb']); self.assertGreater(d['application_rss_mb'],0); self.assertEqual(d['model_server_pids'],0)
 def test_model_manager_rejects_unconfigured_external_and_non_gguf(self):
  cfg={'models':{'language':{'enabled':True,'backend':'llama.cpp','format':'GGUF','model_path':'../secret.gguf','base_url':'http://127.0.0.1:8080/v1','server_executable':'llama-server'}}}
  mgr=LocalModelManager(self.root,lambda:cfg,self.root/'LOGS')
  with self.assertRaises(ValueError):mgr.start('language')
  cfg['models']['language']['model_path']='missing.gguf'
  with self.assertRaises(FileNotFoundError):mgr.start('language')
  cfg['models']['language']['model_path']='ok.gguf'; (self.root/'MODELS/ok.gguf').write_bytes(b'not a model, only a path-check fixture')
  with self.assertRaises(FileNotFoundError):mgr.start('language')
  self.assertFalse(mgr.status()['running'])
 def test_browser_worker_stops_and_no_profile_is_created_when_disabled(self):
  with self.assertRaises(PermissionError):self.browser.open_tab()
  self.assertFalse((self.root/'DATA/browser').exists())

if __name__=='__main__':unittest.main()
