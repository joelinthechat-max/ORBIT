"""Live loop-boundary smoke test: harmless cursor move, post-action screenshot and explicit user review.

Requires an interactive X11 session and a clean ORBIT DATA/LOGS test area. It sends no click or text.
"""
from __future__ import annotations
import json,os,signal,socket,subprocess,sys,time,urllib.request,urllib.error
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from orbit.memory import MemoryStore
from orbit.adapters.computer import DesktopAdapter


def free_port():
 s=socket.socket();s.bind(('127.0.0.1',0));p=s.getsockname()[1];s.close();return p

def req(port,path,data=None):
 raw=json.dumps(data).encode() if data is not None else None
 r=urllib.request.Request(f'http://127.0.0.1:{port}{path}',data=raw,headers={'Content-Type':'application/json'} if raw else {})
 try:
  with urllib.request.urlopen(r,timeout=20) as x:return x.status,json.load(x)
 except urllib.error.HTTPError as e:return e.code,json.load(e)

def main():
 if not os.environ.get('DISPLAY'):
  print('SKIP: X11 DISPLAY unavailable');return 0
 db=ROOT/'DATA/orbit.sqlite3'; cfg=ROOT/'CONFIG/orbit.json'; log=ROOT/'LOGS/orbit.log'; latest=ROOT/'DATA/screenshots/latest.png'
 if any(p.exists() for p in (db,Path(str(db)+'-wal'),Path(str(db)+'-shm'),log,latest)):
  raise RuntimeError('Refusing to run: clean test DB/log/latest screenshot preflight failed; no existing data was changed.')
 original=cfg.read_bytes(); server=None; tid=f'v06obs{int(time.time())}'; created=[]; screenshot_ref=None
 port=free_port(); original_position=None
 try:
  config=json.loads(original); config['port']=port; config['security']['computer_control_enabled']=True; config['models']['language']['enabled']=False;config['models']['vision']['enabled']=False
  cfg.write_text(json.dumps(config,indent=2),encoding='utf-8')
  env={**os.environ,'ORBIT_PORT':str(port)}
  server=subprocess.Popen([str(ROOT/'run_linux.sh')],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True)
  for _ in range(150):
   if server.poll() is not None:raise RuntimeError('ORBIT exited: '+server.stderr.read())
   try:
    code,status=req(port,'/api/status')
    if code==200:break
   except Exception:time.sleep(.1)
  else:raise RuntimeError('ORBIT did not become ready')
  # Capture exact fresh timestamp and current coordinates; move only four pixels, never click or type.
  code,capture=req(port,'/api/computer/screenshot');assert code==200 and capture['captured'],capture
  d=DesktopAdapter(); pos=d.position(); dims=d.dimensions(); width=dims['width'];height=dims['height']
  original_position=pos.copy()
  x=pos['x']+4 if pos['x']+4<width else max(0,pos['x']-4)
  y=pos['y']+4 if pos['y']+4<height else max(0,pos['y']-4)
  params={'x':x,'y':y,'observed_at':capture['at']}
  # Seed one validated, pending registered step in the same USB-local SQLite store.
  memory=MemoryStore(db)
  step={'id':1,'kind':'registered','action':'desktop.move_cursor','title':'Move the pointer four pixels, without clicking or typing','parameters':params,'permission':'B','depends_on':[],'expected':'The pointer moved slightly to the captured target position.','status':'pending','approval':None,'verified':False,'reversible':True,'consequence':'Moves the pointer by four pixels only.'}
  memory.save_task({'id':tid,'objective':'Verify the desktop observe/act/review integration without clicking or typing.','created':time.time(),'status':'planned','steps':[step],'outcome':'','planning_source':'integration-fixture'})
  memory.close()
  code,approval=req(port,'/api/approve',{'task_id':tid,'step_id':1});assert code==200,approval
  code,result=req(port,'/api/execute',{'task_id':tid,'step_id':1});assert code==200 and result.get('awaiting_observation'),result
  assert result['step']['status']=='awaiting_observation' and result['step']['verified'] is False
  code,duplicate=req(port,'/api/execute',{'task_id':tid,'step_id':1});assert 'will not resend' in duplicate.get('error',''),duplicate
  code,review=req(port,'/api/tasks/observe',{'task_id':tid});assert code==202,review
  task=review['task'];assert task['status']=='awaiting_review' and not task['steps'][0]['verified']
  screenshot_ref=task['observation_history'][-1]['screenshot']; screenshot=ROOT/screenshot_ref;created.append(screenshot)
  code,unavailable=req(port,'/api/tasks/replan',{'task_id':tid});assert code==503 and 'Enable a compatible local language model' in unavailable.get('error',''),unavailable
  code,tasks=req(port,'/api/tasks');saved=next(t for t in tasks if t['id']==tid);assert saved['status']=='awaiting_review' and not saved['steps'][0]['verified'] and 'revised_plan_proposal' not in saved
  code,_=req(port,'/api/tasks/verify',{'task_id':tid,'step_id':1,'verified':True,'approved':True});assert code==200,_
  code,tasks=req(port,'/api/tasks');saved=next(t for t in tasks if t['id']==tid)
  assert saved['status']=='completed' and saved['final_verification']['source']=='user_observation' and saved['steps'][0]['verification_source']=='user_observation'
  if server.poll() is None:server.send_signal(signal.SIGINT);server.wait(timeout=10)
  server=None
  server=subprocess.Popen([str(ROOT/'run_linux.sh')],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True)
  for _ in range(100):
   if server.poll() is not None:raise RuntimeError('ORBIT restart exited: '+server.stderr.read())
   try:
    code,tasks=req(port,'/api/tasks');saved=next(t for t in tasks if t['id']==tid);break
   except Exception:time.sleep(.1)
  assert saved['status']=='completed' and saved['steps'][0]['status']=='done' and saved['steps'][0]['verified']
  print('PASS: live bundled HTTP workflow; harmless four-pixel cursor move; Class B approval; action recorded sent/not verified; duplicate execution refused; fresh task-bound screenshot persisted; adaptive replan failed closed with no model configured; explicit user verification; verified state survived restart without input replay.')
  return 0
 finally:
  if server and server.poll() is None:
   server.send_signal(signal.SIGINT)
   try:server.wait(timeout=10)
   except subprocess.TimeoutExpired:server.kill();server.wait(timeout=3)
  if original_position:
   try:subprocess.run(['xdotool','mousemove',str(original_position['x']),str(original_position['y'])],timeout=2,check=False,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
   except Exception:pass
  cfg.write_bytes(original)
  if db.exists():
   memory=MemoryStore(db)
   try:memory.delete_task(tid)
   finally:memory.close()
  for p in created:p.unlink(missing_ok=True)
  if latest.exists():latest.unlink()
  for p in (Path(str(db)+'-wal'),Path(str(db)+'-shm')):p.unlink(missing_ok=True)
  db.unlink(missing_ok=True)
  if log.exists():log.unlink()

if __name__=='__main__':raise SystemExit(main())
