"""Live end-to-end smoke for the USB launcher; creates only disposable test files and refuses non-empty test targets."""
import os,sys,time,json,subprocess,threading,http.server,socketserver,urllib.request,urllib.error,shutil
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from orbit.adapters.computer import DesktopAdapter
ROOT=Path(__file__).resolve().parents[1]; PORT=18765
class Fixture(http.server.BaseHTTPRequestHandler):
 def do_GET(self):
  self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.end_headers();self.wfile.write(b'''<!doctype html><title>ORBIT localhost QA</title><h1>Fixture only; not a real website</h1><input aria-label="Search" id="q"><input type="password" id="secret"><button id="advance" onclick="document.querySelector('#out').innerText='Advanced result observed'">Advance</button><div id="out">Ready</div>''')
 def log_message(self,*a):pass
class FixtureServer(socketserver.TCPServer):allow_reuse_address=True

def req(port,path,body=None):
 data=None if body is None else json.dumps(body).encode(); q=urllib.request.Request(f'http://127.0.0.1:{port}{path}',data=data,headers={'Content-Type':'application/json'} if data else {})
 try:
  with urllib.request.urlopen(q,timeout=20) as r:return r.status,(r.headers.get('Content-Type',''),r.read())
 except urllib.error.HTTPError as e:return e.code,(e.headers.get('Content-Type',''),e.read())
def api(port,path,body=None,code=200):
 status,(ct,raw)=req(port,path,body); obj=json.loads(raw) if 'json' in ct else raw
 assert status==code,(path,status,obj)
 return obj

def main():
 data=ROOT/'DATA'; cfgpath=ROOT/'CONFIG/orbit.json'; db=data/'orbit.sqlite3'; target=ROOT/'DATA/workspace'/'ORBIT Test'; shot=data/'screenshots'/'latest.png'; browserdir=data/'browser'
 if db.exists() or target.exists() or browserdir.exists() or shot.exists():raise SystemExit('Refusing integration: disposable database/workspace/browser/screenshot target already exists; use a clean package copy.')
 original=cfgpath.read_bytes(); desktop=DesktopAdapter(); cursor=desktop.position() if desktop.available else None; fixture=FixtureServer(('127.0.0.1',0),Fixture);threading.Thread(target=fixture.serve_forever,daemon=True).start()
 env=os.environ.copy();env.update(ORBIT_PORT=str(PORT));p=subprocess.Popen([str(ROOT/'run_linux.sh')],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 try:
  for _ in range(80):
   if p.poll() is not None:raise RuntimeError('ORBIT exited: '+(p.stdout.read() if p.stdout else ''))
   try:status=api(PORT,'/api/status');break
   except Exception:time.sleep(.25)
  else:raise TimeoutError('ORBIT startup timeout')
  assert status['version']=='0.6.1' and status['resources']['application_rss_mb']>0 and status['resources']['model_server_rss_mb'] is None
  assert status['storage']['available'] and not status['emergency_stop']
  html=req(PORT,'/')[1][1].decode();assert 'Browser automation' in html and 'BOUNDED AUTONOMY' in html
  catalog=api(PORT,'/api/actions'); ids={x['id']:x for x in catalog};assert {'desktop.capture_screen','desktop.click','browser.navigate','browser.submit_form'}<=ids.keys();assert ids['browser.submit_form']['permission']=='C'
  screencap=api(PORT,'/api/computer/screenshot');assert screencap['captured'] and screencap['width']>0
  assert req(PORT,'/api/computer/latest.png')[0]==200
  windows=api(PORT,'/api/desktop/windows');assert 'windows' in windows
  # External-control setting is disabled by default; API denies even an affirmative client field.
  api(PORT,'/api/computer/action',{'action':'move','x':4,'y':4,'observed_at':screencap['at'],'approved':True},403)
  # Safe Class-A deterministic workflow only, with opt-in and hard action/time bounds.
  api(PORT,'/api/security/flags',{'autonomous_mode_enabled':True,'autonomy':{'max_actions':3,'max_retries':0,'task_timeout_seconds':20}})
  t=api(PORT,'/api/tasks',{'objective':'Create a folder named ORBIT Test inside my workspace, create a text file called report.txt, write a short report about renewable energy in it, and verify that the file was saved correctly.'},201);assert len(t['steps'])==3
  result=api(PORT,'/api/autonomy/run',{'task_id':t['id'],'max_actions':3,'task_timeout_seconds':20,'max_retries':0},200);assert result['status']=='completed' and result['actions']==3
  assert (target/'report.txt').is_file()
  api(PORT,'/api/security/flags',{'computer_control_enabled':True})
  # Move to a nearby point on the sandbox desktop and restore; never click/type.
  move_x=min(screencap['width']-1,3);move_y=min(screencap['height']-1,3)
  moved=api(PORT,'/api/computer/action',{'action':'move','x':move_x,'y':move_y,'observed_at':screencap['at'],'approved':True});assert moved['performed'] and moved['verified'] is False
  api(PORT,'/api/computer/action',{'action':'move','x':move_x,'y':move_y,'observed_at':time.time()-120,'approved':True},400)
  api(PORT,'/api/computer/stop',{},200)
  api(PORT,'/api/computer/action',{'action':'move','x':move_x,'y':move_y,'observed_at':screencap['at'],'approved':True},409)
  api(PORT,'/api/computer/resume',{})
  browser=api(PORT,'/api/browser/config',{'enabled':True,'headless':True,'allow_private_hosts':True,'executable_path':'/usr/bin/chromium'})
  url=f'http://127.0.0.1:{fixture.server_address[1]}/'
  nav=api(PORT,'/api/browser/action',{'action':'navigate','approved':True,'url':url});assert nav['http_status']==200
  page=api(PORT,'/api/browser/action',{'action':'read','approved':True});assert page['page']['title']=='ORBIT localhost QA' and page['untrusted_page_content']
  fill=api(PORT,'/api/browser/action',{'action':'fill','approved':True,'selector':'role:textbox:Search','text':'local test query'});assert fill['verified']
  api(PORT,'/api/browser/action',{'action':'fill','approved':True,'selector':'#secret','text':'never'},400)
  click=api(PORT,'/api/browser/action',{'action':'click','approved':True,'selector':'role:button:Advance'});assert click['verified']
  assert 'Advanced result observed' in api(PORT,'/api/browser/action',{'action':'read','approved':True})['page']['text']
  browser_shot=api(PORT,'/api/browser/action',{'action':'screenshot','approved':True});assert browser_shot['verified'] and req(PORT,'/api/browser/latest.png')[0]==200
  api(PORT,'/api/browser/action',{'action':'close','approved':True})
  # Restore safe defaults in config, then terminate and clean only files proven absent before test.
  cfg=json.loads(original);cfgpath.write_text(json.dumps(cfg,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
  print('PASS: launched bundled Linux USB runtime; live status/resources/storage; real X11 screenshot/window list and latest image; opt-in 3-step Class A autonomous workflow; desktop disabled/fresh timestamp/emergency stop; isolated real Chromium on local fixture, read/fill/password denial/state-changing click/screenshot/close; no real website/model weights used.')
  return 0
 finally:
  try:api(PORT,'/api/browser/action',{'action':'close','approved':True},200)
  except Exception:pass
  try:api(PORT,'/api/computer/resume',{},200)
  except Exception:pass
  if p.poll() is None:p.terminate()
  try:p.wait(timeout=8)
  except subprocess.TimeoutExpired:p.kill();p.wait()
  cfgpath.write_bytes(original)
  fixture.shutdown();fixture.server_close()
  if cursor is not None:
   try:
    restore=DesktopAdapter();restore.screenshot('/tmp/orbit-http-restore.png');restore.move(cursor['x'],cursor['y'],restore.last_observation['at']);Path('/tmp/orbit-http-restore.png').unlink(missing_ok=True)
   except Exception:pass
  for f in (db,Path(str(db)+'-wal'),Path(str(db)+'-shm'),shot):
   try:f.unlink()
   except FileNotFoundError:pass
  if browserdir.exists():shutil.rmtree(browserdir)
  if target.exists():shutil.rmtree(target)
if __name__=='__main__':raise SystemExit(main())
