import sys, time, unittest
import threading
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from orbit.adapters.computer import DesktopAdapter, EMERGENCY_STOP

class FakeScreen:
 def size(self): return type('Size',(),{'width':800,'height':600})()
 def click(self,**kwargs): self.clicked=kwargs

class ComputerSafetyTests(unittest.TestCase):
 def setUp(self):
  EMERGENCY_STOP.clear(); self.adapter=DesktopAdapter.__new__(DesktopAdapter); self.adapter.pg=FakeScreen(); self.adapter._lock=threading.RLock(); self.adapter.backend='pyautogui'; self.adapter.available=True; self.adapter.last_observation={'at':time.time(),'width':800,'height':600,'screen_width':800,'screen_height':600,'origin_x':0,'origin_y':0,'region':None}
 def tearDown(self): EMERGENCY_STOP.clear()
 def test_click_requires_fresh_observation(self):
  stamp=self.adapter.last_observation['at']; self.adapter.click(30,20,stamp); self.assertEqual(self.adapter.pg.clicked['x'],30)
 def test_rejects_stale_coordinate_timestamp(self):
  with self.assertRaises(RuntimeError): self.adapter.click(2,2,time.time()-100)
 def test_rejects_out_of_bounds(self):
  with self.assertRaises(ValueError): self.adapter.click(800,2,self.adapter.last_observation['at'])
 def test_emergency_stop_blocks_action(self):
  EMERGENCY_STOP.set()
  with self.assertRaises(RuntimeError): self.adapter.click(2,2,self.adapter.last_observation['at'])
 def test_destructive_hotkey_denied(self):
  with self.assertRaises(ValueError): self.adapter.hotkey('alt','f4')

if __name__=='__main__': unittest.main()
