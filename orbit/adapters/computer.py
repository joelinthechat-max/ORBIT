"""Real optional desktop I/O. Uses PyAutoGUI when available or fixed-argument X11 tools on Linux."""
from __future__ import annotations
import os, platform, re, shutil, subprocess, threading, time, shlex
from pathlib import Path

EMERGENCY_STOP=threading.Event()
KEYS={'enter':'Return','return':'Return','tab':'Tab','escape':'Escape','esc':'Escape','space':'space','up':'Up','down':'Down','left':'Left','right':'Right','home':'Home','end':'End','pageup':'Page_Up','pagedown':'Page_Down','backspace':'BackSpace','delete':'Delete','ctrl':'ctrl','alt':'alt','shift':'shift','meta':'super','super':'super','win':'super','f1':'F1','f2':'F2','f3':'F3','f4':'F4','f5':'F5','f6':'F6','f7':'F7','f8':'F8','f9':'F9','f10':'F10','f11':'F11','f12':'F12','a':'a','c':'c','v':'v','x':'x','z':'z','s':'s','t':'t','w':'w','r':'r','l':'l','n':'n','o':'o','p':'p','0':'0','1':'1','2':'2','3':'3','4':'4','5':'5','6':'6','7':'7','8':'8','9':'9'}

class DesktopAdapter:
    def __init__(self):
        self.pg=None; self.last_observation=None; self._lock=threading.RLock(); self.backend='unavailable'; self.available=False; self.reason='No supported interactive desktop backend was found.'
        try:
            import pyautogui
            import PIL.ImageGrab
            self.pg=pyautogui; self.pg.FAILSAFE=True; self.pg.PAUSE=.1
            self.backend='pyautogui'; self.available=True; self.reason=''
        except Exception:
            if platform.system()=='Linux' and os.environ.get('DISPLAY') and shutil.which('xdotool'):
                try:
                    from PIL import ImageGrab
                    ImageGrab.grab()
                    self.backend='x11-xdotool'; self.available=True; self.reason=''
                except Exception as e: self.reason=f'X11 capture unavailable: {e}'
            elif platform.system()=='Linux' and os.environ.get('WAYLAND_DISPLAY'):
                self.reason='Wayland session detected; this adapter does not bypass compositor input/screenshot restrictions.'
            else: self.reason='PyAutoGUI and an interactive X11 fallback are unavailable.'

    @staticmethod
    def platform_info():
        probe=DesktopAdapter()
        return {'os':platform.system(),'available':probe.available,'backend':probe.backend,'supported_backend':probe.backend,'wayland_note':'No Wayland global-input bypass is attempted; compositor policy may deny capture/input.','reason':probe.reason,'multiple_monitor_support':'Primary display only; no claim of multi-monitor coordinate support.'}

    def _need(self):
        if not self.available: raise RuntimeError(self.reason)
        if EMERGENCY_STOP.is_set(): raise RuntimeError('Emergency stop is active')

    def dimensions(self):
        self._need()
        if self.pg:
            size=self.pg.size(); return {'width':int(size.width),'height':int(size.height)}
        from PIL import ImageGrab
        img=ImageGrab.grab(); return {'width':int(img.width),'height':int(img.height)}

    def _run(self,args,timeout=3,input_text=None):
        self._need()
        kwargs={'stdout':subprocess.PIPE,'stderr':subprocess.PIPE,'text':True,'timeout':timeout,'check':False}
        if input_text is None: kwargs['stdin']=subprocess.DEVNULL
        p=subprocess.run(args,input=input_text,**kwargs)
        if p.returncode: raise RuntimeError((p.stderr or 'Desktop command failed').strip()[:400])
        return p.stdout.strip()

    def _x11_active(self):
        try: wid=self._run(['xdotool','getactivewindow'])
        except RuntimeError: wid=self._run(['xdotool','getwindowfocus'])
        if not wid: raise RuntimeError('The X11 session did not expose an active/focused window.')
        name=self._run(['xdotool','getwindowname',wid])
        geo=self._run(['xdotool','getwindowgeometry','--shell',wid])
        data={k:int(v) for line in geo.splitlines() if '=' in line for k,v in [line.split('=',1)] if k in {'X','Y','WIDTH','HEIGHT'}}
        return {'window_id':wid,'title':name[:300],'x':data.get('X',0),'y':data.get('Y',0),'width':data.get('WIDTH',0),'height':data.get('HEIGHT',0),'observed_at':time.time()}

    def active_window(self):
        self._need()
        if self.backend=='x11-xdotool': return self._x11_active()
        w=getattr(self.pg,'getActiveWindow',lambda:None)()
        if not w: return {'window_id':None,'title':None,'x':0,'y':0,'width':0,'height':0,'observed_at':time.time()}
        return {'window_id':getattr(w,'id',None),'title':str(getattr(w,'title',''))[:300],'x':int(w.left),'y':int(w.top),'width':int(w.width),'height':int(w.height),'observed_at':time.time()}

    def list_windows(self):
        self._need()
        if self.backend=='x11-xdotool':
            ids=self._run(['xdotool','search','--onlyvisible','--name','.'],timeout=5).splitlines()[:100]; out=[]
            for wid in ids:
                try:
                    title=self._run(['xdotool','getwindowname',wid],timeout=1)
                    geo=self._run(['xdotool','getwindowgeometry','--shell',wid],timeout=1)
                    d={k:int(v) for line in geo.splitlines() if '=' in line for k,v in [line.split('=',1)] if k in {'X','Y','WIDTH','HEIGHT'}}
                    out.append({'window_id':wid,'title':title[:300],'x':d.get('X',0),'y':d.get('Y',0),'width':d.get('WIDTH',0),'height':d.get('HEIGHT',0)})
                except Exception: continue
            return {'windows':out,'observed_at':time.time(),'verified':True,'summary':f'Found {len(out)} visible windows.'}
        win=getattr(self.pg,'getAllWindows',lambda:[])(); out=[]
        for w in win[:100]:
            out.append({'window_id':getattr(w,'id',None),'title':str(getattr(w,'title',''))[:300],'x':int(w.left),'y':int(w.top),'width':int(w.width),'height':int(w.height)})
        return {'windows':out,'observed_at':time.time(),'verified':True,'summary':f'Found {len(out)} visible windows.'}

    def discover_applications(self):
        self._need(); found=[]
        if platform.system()=='Linux':
            roots=[Path('/usr/share/applications'),Path.home()/'.local/share/applications']
            for root in roots:
                if not root.is_dir(): continue
                for p in sorted(root.glob('*.desktop'))[:500]:
                    try:
                        text=p.read_text(encoding='utf-8',errors='replace')
                        if re.search(r'(?m)^NoDisplay=true\s*$',text): continue
                        name=re.search(r'(?m)^Name=(.+)$',text); exec_line=re.search(r'(?m)^Exec=(.+)$',text)
                        if name and exec_line:
                            try:
                                argv=[x for x in shlex.split(exec_line.group(1)) if not re.fullmatch(r'%[fFuUdDnNickvm]',x)]
                                executable=shutil.which(argv[0]) if argv and not Path(argv[0]).is_absolute() else (argv[0] if argv else '')
                                if executable and Path(executable).is_file(): found.append({'id':p.stem,'name':name.group(1)[:100],'path':str(Path(executable).resolve()),'launch_allowed':False})
                            except (ValueError,OSError,IndexError): pass
                    except OSError: continue
        elif os.name=='nt':
            roots=[Path(os.environ.get('PROGRAMDATA','C:/ProgramData'))/'Microsoft/Windows/Start Menu/Programs',Path(os.environ.get('APPDATA',''))/'Microsoft/Windows/Start Menu/Programs']
            for root in roots:
                if root.is_dir():
                    for p in list(root.rglob('*.lnk'))[:500]: found.append({'id':str(p.resolve()),'name':p.stem[:100],'path':str(p.resolve()),'launch_allowed':False})
        return {'applications':found[:500],'verified':True,'summary':f'Discovered {len(found[:500])} application shortcuts. Launch remains blocked unless the executable is explicitly allowlisted.'}

    def screenshot(self,path=None,region=None,scope='screen',max_dimension=1280):
        with self._lock:
            self._need(); screen=self.dimensions(); origin=(0,0); crop=None
            if scope=='active_window':
                win=self.active_window(); origin=(win['x'],win['y']); crop=(win['x'],win['y'],win['x']+win['width'],win['y']+win['height'])
            elif scope!='screen': raise ValueError('scope must be screen or active_window')
            if region is not None:
                if not isinstance(region,(list,tuple)) or len(region)!=4 or any(type(v) is not int for v in region): raise ValueError('region must be [x,y,width,height] integers')
                x,y,w,h=region
                if w<1 or h<1 or x<0 or y<0 or x+w>screen['width'] or y+h>screen['height']: raise ValueError('screenshot region outside screen bounds')
                crop=(x,y,x+w,y+h); origin=(x,y)
            if self.pg:
                img=self.pg.screenshot(region=(crop[0],crop[1],crop[2]-crop[0],crop[3]-crop[1])) if crop else self.pg.screenshot()
            else:
                from PIL import ImageGrab
                img=ImageGrab.grab(bbox=crop) if crop else ImageGrab.grab()
            original=(img.width,img.height); cap=max(320,min(int(max_dimension),1920))
            if max(img.size)>cap:
                img.thumbnail((cap,cap))
            stamp=time.time(); self.last_observation={'at':stamp,'width':original[0],'height':original[1],'screen_width':screen['width'],'screen_height':screen['height'],'origin_x':origin[0],'origin_y':origin[1],'captured_width':img.width,'captured_height':img.height,'scope':scope,'region':region}
            if path:
                target=Path(path); target.parent.mkdir(parents=True,exist_ok=True); img.save(target,format='PNG')
            return img

    def _validate_xy(self,x,y,observed_at):
        self._need(); obs=self.last_observation
        if not obs or type(observed_at) not in (int,float) or observed_at!=obs['at'] or time.time()-observed_at>60: raise RuntimeError('Fresh screenshot observation required (maximum age 60 seconds)')
        dims=self.dimensions()
        if dims['width']!=obs['screen_width'] or dims['height']!=obs['screen_height']: raise RuntimeError('Screen dimensions changed; capture a fresh screenshot')
        if type(x) is not int or type(y) is not int or not(0<=x<dims['width'] and 0<=y<dims['height']): raise ValueError('Coordinates outside current screen bounds')
        if not(obs['origin_x']<=x<obs['origin_x']+obs['width'] and obs['origin_y']<=y<obs['origin_y']+obs['height']): raise ValueError('Coordinates outside the observed screenshot region')
        return dims

    def _x11_click(self,x,y,button='left',clicks=1):
        code={'left':'1','middle':'2','right':'3'}[button]
        self._run(['xdotool','mousemove','--sync',str(x),str(y)])
        self._run(['xdotool','click','--clearmodifiers','--repeat',str(clicks),'--delay','100',code])

    def click(self,x,y,observed_at,button='left',clicks=1):
        with self._lock:
            self._validate_xy(x,y,observed_at)
            if button not in {'left','right','middle'} or clicks not in {1,2}: raise ValueError('Unsupported click parameters')
            if self.pg: self.pg.click(x=x,y=y,button=button,clicks=clicks)
            else: self._x11_click(x,y,button,clicks)

    def move(self,x,y,observed_at):
        with self._lock:
            self._validate_xy(x,y,observed_at)
            if self.pg: self.pg.moveTo(x,y,duration=.15)
            else: self._run(['xdotool','mousemove','--sync',str(x),str(y)])

    def scroll(self,amount,x,y,observed_at):
        with self._lock:
            self._validate_xy(x,y,observed_at); amount=max(-10,min(int(amount),10))
            if not amount: return
            if self.pg: self.pg.moveTo(x,y); self.pg.scroll(amount)
            else:
                self._run(['xdotool','mousemove','--sync',str(x),str(y)])
                self._run(['xdotool','click','--repeat',str(abs(amount)),'4' if amount>0 else '5'])

    def drag(self,x1,y1,x2,y2,observed_at,button='left'):
        with self._lock:
            self._validate_xy(x1,y1,observed_at); self._validate_xy(x2,y2,observed_at)
            if button not in {'left','right','middle'}: raise ValueError('Unsupported drag button')
            if self.pg: self.pg.moveTo(x1,y1); self.pg.dragTo(x2,y2,duration=.35,button=button)
            else:
                b={'left':'1','middle':'2','right':'3'}[button]
                self._run(['xdotool','mousemove','--sync',str(x1),str(y1),'mousedown',b])
                try: self._run(['xdotool','mousemove','--sync',str(x2),str(y2)])
                finally: self._run(['xdotool','mouseup',b])

    def type_text(self,text):
        with self._lock:
            self._need()
            if not isinstance(text,str) or len(text)>2000: raise ValueError('Text input must be at most 2000 characters')
            if self.pg: self.pg.write(text,interval=.005)
            else: self._run(['xdotool','type','--clearmodifiers','--delay','1','--',text],timeout=10)

    def press_key(self,key):
        if not isinstance(key,str) or key.lower() not in KEYS: raise ValueError('Key is not in the safe key allowlist')
        mapped=KEYS[key.lower()]
        if key.lower() in {'delete','backspace'}: raise ValueError('Destructive editing key is denied; select a reviewed text-edit action instead')
        self.hotkey(key)

    def hotkey(self,*keys):
        with self._lock:
            self._need()
            if not 1<=len(keys)<=4: raise ValueError('Hotkey must contain 1-4 keys')
            lowered=[str(k).lower() for k in keys]
            if any(k not in KEYS for k in lowered): raise ValueError('Hotkey contains a key outside the allowlist')
            if set(lowered)&{'alt','f4','delete','backspace','super','win','meta'}: raise ValueError('Potentially destructive/system shortcut denied')
            if len(lowered)>1 and not(set(lowered)&{'ctrl','shift','alt'}): raise ValueError('Multi-key shortcuts need a modifier')
            if self.pg: self.pg.hotkey(*lowered)
            else: self._run(['xdotool','key','--clearmodifiers','+'.join(KEYS[k] for k in lowered)])

    def clipboard_read(self):
        with self._lock:
            self._need()
            if os.name=='nt':
                try:
                    import pyperclip
                    text=pyperclip.paste()
                except Exception as e: raise RuntimeError('Windows clipboard adapter is not installed/configured; install pyperclip into VENDOR/WINDOWS to enable it.') from e
            elif shutil.which('xclip'): text=self._run(['xclip','-selection','clipboard','-o'],timeout=2)
            else: raise RuntimeError('Clipboard read requires xclip on X11.')
            return {'text':text[:2000],'truncated':len(text)>2000,'verified':True,'summary':'Read current clipboard text (sensitive content; Class C approval required).'}

    def clipboard_write(self,text):
        with self._lock:
            self._need()
            if not isinstance(text,str) or len(text)>2000: raise ValueError('Clipboard text is limited to 2,000 characters')
            if os.name=='nt':
                try:
                    import pyperclip
                    pyperclip.copy(text)
                except Exception as e: raise RuntimeError('Windows clipboard adapter is not installed/configured.') from e
            elif shutil.which('xclip'):
                self._run(['xclip','-selection','clipboard'],timeout=2,input_text=text)
            else: raise RuntimeError('Clipboard write requires xclip on X11.')
            return {'verified':True,'summary':'Wrote the reviewed text to the local clipboard.'}

    def activate_window(self,window_id,observed_at):
        self._need()
        if time.time()-float(observed_at)>60: raise RuntimeError('Refresh window list before activating a window')
        if self.backend=='x11-xdotool': self._run(['xdotool','windowactivate','--sync',str(int(window_id))])
        else:
            win=getattr(self.pg,'getWindow',lambda _id:None)(int(window_id))
            if not win: raise RuntimeError('Window handle is not available through this backend')
            win.activate()
        return {'verified':True,'summary':f'Activated window {window_id}.'}

    def close_window(self,window_id,observed_at):
        self._need()
        if time.time()-float(observed_at)>60: raise RuntimeError('Refresh window list before closing a window')
        if self.backend=='x11-xdotool': self._run(['xdotool','windowclose',str(int(window_id))])
        else:
            win=getattr(self.pg,'getWindow',lambda _id:None)(int(window_id))
            if not win: raise RuntimeError('Window handle is not available through this backend')
            win.close()
        return {'verified':True,'summary':f'Sent a close request to window {window_id}; application save dialogs may remain open.'}

    def launch_application(self,app_id,allowlist):
        self._need(); item=allowlist.get(app_id) if isinstance(allowlist,dict) else None
        if not isinstance(item,str) or not item.strip(): raise PermissionError('Application is not explicitly allowlisted in local configuration')
        executable=Path(item).expanduser()
        if not executable.is_absolute():
            found=shutil.which(item)
            if not found: raise FileNotFoundError('Allowlisted application was not found on this computer')
            executable=Path(found)
        if not executable.is_file(): raise FileNotFoundError('Allowlisted application executable does not exist')
        if os.name=='nt' and executable.suffix.lower()=='.lnk':
            os.startfile(str(executable))
            return {'pid':None,'verified':True,'summary':f'Opened user-allowlisted Windows shortcut {app_id} through the OS shell association.'}
        proc=subprocess.Popen([str(executable)],cwd=str(Path(__file__).resolve().parents[2]),shell=False,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,close_fds=(os.name!='nt'))
        time.sleep(.2)
        return {'pid':proc.pid,'verified':proc.poll() is None,'summary':f'Launched user-allowlisted application {app_id} (process {proc.pid}).'}

    def position(self):
        self._need()
        if self.pg: p=self.pg.position(); return {'x':int(p.x),'y':int(p.y)}
        out=self._run(['xdotool','getmouselocation','--shell']); d=dict(line.split('=',1) for line in out.splitlines() if '=' in line); return {'x':int(d['X']),'y':int(d['Y'])}
