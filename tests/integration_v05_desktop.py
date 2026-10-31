"""Optional real X11 smoke test. It captures the sandbox desktop and only moves/restores the cursor; never clicks or types."""
import os,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import orbit
from orbit.adapters.computer import DesktopAdapter,EMERGENCY_STOP

def main():
 if not os.environ.get('DISPLAY'):
  print('SKIP: no X11 DISPLAY');return 0
 d=DesktopAdapter()
 if not d.available:
  print('SKIP: desktop backend unavailable:',d.reason);return 0
 try:
  windows=d.list_windows(); active=d.active_window(); img=d.screenshot('/tmp/orbit-desktop-smoke.png'); o=d.last_observation
  assert img.width>0 and img.height>0 and o['screen_width']>0 and o['screen_height']>0
  original=d.position(); x=min(o['screen_width']-1,max(0,original['x']+4)); y=min(o['screen_height']-1,max(0,original['y']+4)); d.move(x,y,o['at']); d.move(original['x'],original['y'],o['at'])
  try:d.move(x,y,time.time()-100)
  except RuntimeError:pass
  else:raise AssertionError('stale coordinate unexpectedly accepted')
  EMERGENCY_STOP.set()
  try:d.move(x,y,o['at'])
  except RuntimeError:pass
  else:raise AssertionError('emergency stop did not block input')
  finally:EMERGENCY_STOP.clear()
  print(f'PASS: {d.backend} real screenshot {img.size}, {len(windows["windows"])} visible window(s), active-window metadata, cursor move/restore, stale timestamp denial, emergency stop.')
 except Exception as e:
  print('FAIL:',type(e).__name__,str(e));return 1
 return 0
if __name__=='__main__':raise SystemExit(main())
