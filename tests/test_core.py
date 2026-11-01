import sys, unittest, tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from orbit.planner import Planner
from orbit.safety import SafetyPolicy
class CoreTests(unittest.TestCase):
 def test_create_file_plan(self):
  x=Planner().plan("Create a file named note.txt with the text: Hello")
  self.assertEqual(x[0].kind,"file_write"); self.assertEqual(x[0].detail,"note.txt\nHello")
 def test_empty_rejected(self):
  with self.assertRaises(ValueError): Planner().plan(" ")
 def test_risky_actions_gated(self):
  p=SafetyPolicy()
  for k in ("delete","shell","click","external_send"): self.assertTrue(p.assess({"kind":k}).approval_required)
 def test_path_traversal_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(ValueError): SafetyPolicy().safe_path(Path(d),"../escape")
 def test_path_inside_allowed(self):
  with tempfile.TemporaryDirectory() as d: self.assertEqual(SafetyPolicy().safe_path(Path(d),"ok.txt"), (Path(d)/"ok.txt").resolve())
if __name__=="__main__": unittest.main()
