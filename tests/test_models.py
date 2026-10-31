import sys,unittest,tempfile,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from orbit.adapters.models import OpenAICompatibleModel
from orbit.actions import ActionRegistry

class FakeModel(OpenAICompatibleModel):
 def __init__(self,text): self.text=text; self.model='mock-model'
 def complete(self,prompt,system='',max_tokens=512): return self.text

class ModelAdapterTests(unittest.TestCase):
 def setUp(self): self.tmp=tempfile.TemporaryDirectory(); self.registry=ActionRegistry(Path(self.tmp.name))
 def tearDown(self): self.tmp.cleanup()
 def test_rejects_remote_endpoint(self):
  with self.assertRaises(ValueError): OpenAICompatibleModel('https://example.com/v1')
 def test_accepts_valid_multi_step_registered_plan(self):
  steps=[{'id':1,'action':'workspace.create_directory','description':'Create folder','parameters':{'path':'reports'},'depends_on':[],'expected':'Folder exists'}, {'id':2,'action':'workspace.create_file','description':'Write report','parameters':{'path':'reports/a.txt','content':'hello'},'depends_on':[1],'expected':'File written'}, {'id':3,'action':'workspace.verify_file','description':'Verify report','parameters':{'path':'reports/a.txt','expected_content':'hello'},'depends_on':[2],'expected':'Contents match'}]
  fake=FakeModel(json.dumps({'objective':'new file','steps':steps})); result=fake.propose_plan('create and verify',registry=self.registry)
  self.assertEqual(len(result['steps']),3); self.assertEqual(result['steps'][2]['depends_on'],[2])
 def test_rejects_unknown_action_and_invalid_parameters(self):
  for action,params in [('shell.exec',{'command':'whoami'}),('workspace.create_file',{'path':'../bad.txt','content':'x'})]:
   fake=FakeModel(json.dumps({'objective':'bad','steps':[{'id':1,'action':action,'description':'No','parameters':params,'depends_on':[],'expected':'bad'}]}))
   with self.assertRaises(ValueError): fake.propose_plan('do something',registry=self.registry)
 def test_rejects_forward_dependency(self):
  fake=FakeModel(json.dumps({'objective':'bad','steps':[{'id':1,'action':'workspace.list','description':'List','parameters':{'path':'.'},'depends_on':[2],'expected':'Listed'}]}))
  with self.assertRaises(ValueError): fake.propose_plan('inspect',registry=self.registry)
 def test_rejects_malformed_json(self):
  with self.assertRaises(ValueError): FakeModel('not json').propose_plan('task',registry=self.registry)

if __name__=='__main__':unittest.main()
