"""Registered, bounded actions; model plans cannot execute outside this catalogue."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Any
import hashlib, json, shutil, time, os

READABLE={'.txt','.md','.csv','.json','.log'}
MAX_TEXT=100_000
MAX_READ=1_000_000
MAX_COPY=50_000_000

def _sha256_file(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): digest.update(chunk)
    return digest.digest()

@dataclass(frozen=True)
class ActionSpec:
    id:str
    description:str
    permission:str
    schema:dict[str,str]
    timeout_seconds:int
    reversible:bool
    consequence:str
    handler:Callable[[dict[str,Any]],dict[str,Any]]

class ActionRegistry:
    """Actions operate inside one workspace. External command execution is absent by design."""
    def __init__(self,root:Path,desktop=None,browser=None,config_getter=None,screenshot_dir=None):
        self.root=Path(root).resolve(); self.root.mkdir(parents=True,exist_ok=True); self.actions={}
        self.desktop=desktop; self.browser=browser; self.config_getter=config_getter or (lambda:{}); self.screenshot_dir=Path(screenshot_dir or self.root/'screenshots')
        self._register_defaults()
    def _register(self,aid,description,permission,schema,timeout,reversible,consequence,handler):
        if aid in self.actions: raise ValueError(f'Duplicate action id: {aid}')
        self.actions[aid]=ActionSpec(aid,description,permission,schema,timeout,reversible,consequence,handler)
    def _path(self,rel,allow_root=False):
        if not isinstance(rel,str) or not rel or len(rel)>500: raise ValueError('path must be a non-empty relative workspace path')
        if '\\' in rel or ':' in rel or any(ord(c)<32 for c in rel): raise ValueError('Use portable forward-slash workspace paths without drive names or control characters')
        p=Path(rel)
        if p.is_absolute(): raise ValueError('absolute paths are not allowed')
        target=(self.root/p).resolve()
        if target!=self.root and self.root not in target.parents: raise ValueError('path escapes the workspace')
        if target==self.root and not allow_root: raise ValueError('workspace root is not a file path')
        cur=self.root
        for part in p.parts:
            if part in {'.',''}: continue
            cur=cur/part
            if cur.is_symlink(): raise ValueError('symlink paths are not permitted')
        return target
    def _check(self,aid,params):
        spec=self.actions.get(aid)
        if spec is None: raise ValueError(f'Unknown action: {aid}')
        if not isinstance(params,dict): raise ValueError('parameters must be an object')
        expected=set(spec.schema); actual=set(params)
        if actual!=expected: raise ValueError(f'{aid} requires exactly these parameters: {", ".join(sorted(expected))}')
        for name,kind in spec.schema.items():
            value=params[name]
            if kind=='str' and (not isinstance(value,str) or not value.strip()): raise ValueError(f'{name} must be a non-empty string')
            if kind=='text' and (not isinstance(value,str) or len(value)>MAX_TEXT): raise ValueError(f'{name} must be text of at most {MAX_TEXT} characters')
            if kind=='int' and type(value) is not int: raise ValueError(f'{name} must be an integer')
            if kind=='number' and (isinstance(value,bool) or not isinstance(value,(int,float))): raise ValueError(f'{name} must be a number')
            if kind=='list' and not isinstance(value,list): raise ValueError(f'{name} must be a list')
            if kind=='nullable-list' and value is not None and not isinstance(value,list): raise ValueError(f'{name} must be a list or null')
            if kind in {'str','text'} and len(value)>200_000: raise ValueError(f'{name} exceeds the generic action-input limit')
        # Validate all file paths before anything is executed.
        for name,kind in spec.schema.items():
            if kind=='path': self._path(params[name],allow_root=aid in {'workspace.list','workspace.search'})
        if aid=='workspace.search' and len(params['query'])>200: raise ValueError('query is too long')
        if aid=='desktop.capture_screen':
            if params['scope'] not in {'screen','active_window'}: raise ValueError('scope must be screen or active_window')
            if type(params['max_dimension']) is not int or not 320<=params['max_dimension']<=1920: raise ValueError('max_dimension must be 320-1920')
            region=params['region']
            if region is not None and (len(region) not in {0,4} or any(type(x) is not int for x in region)): raise ValueError('region must be empty or [x,y,width,height] integers')
            if region and (region[2]<1 or region[3]<1): raise ValueError('region width and height must be positive')
        if aid=='desktop.launch_approved_app' and params['app_id'] not in self.config_getter().get('security',{}).get('approved_applications',{}): raise ValueError('Application ID is not explicitly allowlisted in local configuration')
        if aid=='desktop.click' and (params['button'] not in {'left','right','middle'} or params['clicks'] not in {1,2}): raise ValueError('Invalid desktop click button/count')
        if aid=='desktop.drag' and params['button'] not in {'left','right','middle'}: raise ValueError('Invalid desktop drag button')
        if aid=='desktop.hotkey':
            if not 1<=len(params['keys'])<=4 or any(not isinstance(x,str) for x in params['keys']): raise ValueError('keys must contain 1-4 strings')
            lowered=[x.lower() for x in params['keys']]
            if any(x not in {'enter','return','tab','escape','esc','space','up','down','left','right','home','end','pageup','pagedown','ctrl','alt','shift','meta','super','win','f1','f2','f3','f4','f5','f6','f7','f8','f9','f10','f11','f12','a','c','v','x','z','s','t','w','r','l','n','o','p','0','1','2','3','4','5','6','7','8','9'} for x in lowered): raise ValueError('Hotkey contains an unsupported key')
            if set(lowered)&{'alt','f4','delete','backspace','super','win','meta'}: raise ValueError('Potentially destructive/system shortcut denied')
            if len(lowered)>1 and not(set(lowered)&{'ctrl','shift','alt'}): raise ValueError('Multi-key shortcut needs a modifier')
        if aid=='desktop.press_key' and params['key'].lower() not in {'enter','return','tab','escape','esc','space','up','down','left','right','home','end','pageup','pagedown','f1','f2','f3','f4','f5','f6','f7','f8','f9','f10','f11','f12'}: raise ValueError('Key is not in the safe navigation key allowlist')
        if aid in {'browser.navigate','browser.open_tab'}:
            url=params['url']
            if aid=='browser.open_tab' and url=='about:blank': pass
            else: self.browser._safe_url(url)
        if aid=='browser.press' and params['key'] not in {'Enter','Tab','Escape','ArrowUp','ArrowDown','ArrowLeft','ArrowRight','Home','End','PageUp','PageDown','Space'}: raise ValueError('Browser key is not allowlisted')
        if aid=='browser.scroll' and abs(params['amount'])>2000: raise ValueError('Browser scroll is limited to 2,000 pixels')
        if aid in {'workspace.copy_file','workspace.move_file','workspace.rename_file'}:
            s=self._path(params['source']); d=self._path(params['destination'])
            if s==d: raise ValueError('source and destination must differ')
            if aid=='workspace.rename_file' and s.parent!=d.parent: raise ValueError('rename_file must stay in the same folder; use move_file for another folder')
        if aid=='workspace.create_file' and len(params['content'])>MAX_TEXT: raise ValueError(f'content is limited to {MAX_TEXT} characters')
        if aid in {'workspace.create_file','workspace.edit_file'} and Path(params['path']).suffix.lower() not in {'.txt','.md','.csv','.json'}: raise ValueError('Text creation/editing supports .txt, .md, .csv and .json files')
        if aid=='workspace.edit_file' and self._path(params['path']).exists() and not self._path(params['path']).is_file(): raise ValueError('Only regular files can be edited')
        return spec
    def validate(self,aid,params):
        spec=self._check(aid,params)
        return {'action':spec.id,'permission':spec.permission,'description':spec.description,'timeout_seconds':spec.timeout_seconds,'reversible':spec.reversible,'consequence':spec.consequence,'parameters':dict(params)}
    def catalog(self):
        return [{'id':s.id,'description':s.description,'permission':s.permission,'parameters':s.schema,'timeout_seconds':s.timeout_seconds,'reversible':s.reversible,'consequence':s.consequence} for s in self.actions.values()]
    def execute(self,aid,params):
        spec=self._check(aid,params)
        started=time.monotonic(); result=spec.handler(params)
        elapsed=time.monotonic()-started
        # Current handlers are synchronous local filesystem operations with bounded input/work.
        if elapsed>spec.timeout_seconds: raise TimeoutError(f'{aid} exceeded {spec.timeout_seconds}s timeout')
        if not isinstance(result,dict) or (result.get('verified') is not True and result.get('action_sent') is not True): raise RuntimeError(f'{aid} neither verified its result nor reported a sent action')
        return {**result,'action':aid,'elapsed_seconds':round(elapsed,4),'verified':result.get('verified') is True,'action_sent':result.get('action_sent') is True}
    def _register_defaults(self):
        def list_files(p):
            root=self._path(p['path'],True); items=[]
            for x in sorted(root.iterdir(),key=lambda q:q.name.casefold())[:500]:
                if x.is_symlink(): continue
                items.append({'name':x.name,'type':'directory' if x.is_dir() else 'file','size':x.stat().st_size if x.is_file() else None})
            return {'items':items,'verified':True,'summary':f'Listed {len(items)} workspace entries.'}
        def search(p):
            root=self._path(p['path'],True); query=p['query'].casefold(); results=[]
            for count,x in enumerate(root.rglob('*')):
                if count>=5000: break
                if x.is_symlink(): continue
                if query in x.name.casefold(): results.append(str(x.relative_to(self.root)));
                if len(results)>=200: break
            return {'matches':results,'verified':True,'summary':f'Found {len(results)} matching file or folder names.'}
        def read_file(p):
            target=self._path(p['path'])
            if target.suffix.lower() not in READABLE: raise ValueError('Supported readable formats: .txt, .md, .csv, .json, .log')
            if not target.is_file(): raise FileNotFoundError(p['path'])
            if target.stat().st_size>MAX_READ: raise ValueError('File exceeds 1 MB read limit')
            text=target.read_text(encoding='utf-8'); return {'text':text,'verified':True,'summary':f'Read {len(text)} characters from {p["path"]}.'}
        def verify_file(p):
            target=self._path(p['path'])
            if not target.is_file(): raise FileNotFoundError(p['path'])
            if target.stat().st_size>MAX_READ: raise ValueError('File exceeds 1 MB verification limit')
            actual=target.read_text(encoding='utf-8')
            if actual!=p['expected_content']: raise RuntimeError('Saved file differs from the expected content')
            return {'verified':True,'summary':f'Verified exact file contents for {p["path"]}.'}
        def create_dir(p):
            t=self._path(p['path']);
            if t.exists() and not t.is_dir(): raise FileExistsError(p['path'])
            t.mkdir(parents=True,exist_ok=True)
            if not t.is_dir(): raise RuntimeError('Directory verification failed')
            return {'verified':True,'summary':f'Folder ready: {p["path"]}.'}
        def create_file(p):
            t=self._path(p['path'])
            if not t.parent.is_dir(): raise FileNotFoundError('Parent folder is missing; add an explicit workspace.create_directory step first')
            if t.exists():
                if t.is_file() and t.read_text(encoding='utf-8')==p['content']: return {'verified':True,'summary':f'File already exists with matching contents: {p["path"]}.'}
                raise FileExistsError('Refusing to overwrite an existing file; use the approval-gated edit_file action.')
            with t.open('x',encoding='utf-8',newline='') as f: f.write(p['content']); f.flush(); os.fsync(f.fileno())
            if not t.is_file() or t.read_text(encoding='utf-8')!=p['content']: raise RuntimeError('File content verification failed')
            return {'verified':True,'summary':f'Created and verified {p["path"]}.'}
        def edit_file(p):
            t=self._path(p['path']);
            if not t.is_file(): raise FileNotFoundError(p['path'])
            if t.stat().st_size>MAX_READ: raise ValueError('Existing file exceeds 1 MB edit limit')
            temp=t.with_name(t.name+'.orbit-tmp')
            if temp.exists(): raise FileExistsError('Temporary replacement file already exists')
            try:
                with temp.open('x',encoding='utf-8',newline='') as f: f.write(p['content']); f.flush(); os.fsync(f.fileno())
                temp.replace(t)
            finally: temp.unlink(missing_ok=True)
            if t.read_text(encoding='utf-8')!=p['content']: raise RuntimeError('Edited file verification failed')
            return {'verified':True,'summary':f'Edited and verified {p["path"]}.'}
        def copy_file(p):
            s=self._path(p['source']); d=self._path(p['destination'])
            if not s.is_file(): raise FileNotFoundError(p['source'])
            if s.stat().st_size>MAX_COPY: raise ValueError('Copy limit is 50 MB')
            if not d.parent.is_dir(): raise FileNotFoundError('Copy destination folder must exist; create it with a separate approved action')
            if d.exists(): raise FileExistsError('Refusing to overwrite destination')
            try:
                shutil.copy2(s,d)
                with d.open('rb') as f: os.fsync(f.fileno())
                if not d.is_file() or _sha256_file(s)!=_sha256_file(d): raise RuntimeError('Copy verification failed')
            except Exception:
                d.unlink(missing_ok=True); raise
            return {'verified':True,'summary':f'Copied and verified {p["source"]} to {p["destination"]}.'}
        def move_file(p):
            s=self._path(p['source']); d=self._path(p['destination'])
            if not s.is_file(): raise FileNotFoundError(p['source'])
            if s.stat().st_size>MAX_COPY: raise ValueError('Move verification limit is 50 MB')
            if not d.parent.is_dir(): raise FileNotFoundError('Move destination folder must exist; create it with a separate approved action')
            if d.exists(): raise FileExistsError('Refusing to overwrite destination')
            before=_sha256_file(s); s.rename(d)
            if s.exists() or not d.is_file() or _sha256_file(d)!=before: raise RuntimeError('Move verification failed')
            return {'verified':True,'summary':f'Moved and verified {p["source"]} to {p["destination"]}.'}
        def delete_file(p):
            t=self._path(p['path'])
            if not t.is_file(): raise FileNotFoundError(p['path'])
            t.unlink()
            if t.exists(): raise RuntimeError('Delete verification failed')
            return {'verified':True,'summary':f'Deleted {p["path"]}.'}
        def rename(p):
            s=self._path(p['source']); d=self._path(p['destination'])
            if not s.is_file(): raise FileNotFoundError(p['source'])
            if d.exists(): raise FileExistsError('Refusing to overwrite destination')
            s.rename(d)
            if s.exists() or not d.is_file(): raise RuntimeError('Rename verification failed')
            return {'verified':True,'summary':f'Renamed to {p["destination"]}.'}
        specs=[
          ('workspace.list','List files and folders in the workspace','A',{'path':'path'},3,True,'Read-only listing',list_files),
          ('workspace.search','Search workspace paths by filename','A',{'path':'path','query':'str'},5,True,'Read-only filename search (maximum 5,000 examined entries)',search),
          ('workspace.read_file','Read supported UTF-8 text files','A',{'path':'path'},3,True,'Read-only; supported extensions and size limits apply',read_file),
          ('workspace.verify_file','Verify exact contents of a supported text file','A',{'path':'path','expected_content':'text'},3,True,'Read-only verification; file contents are not changed',verify_file),
          ('workspace.create_directory','Create a workspace folder','A',{'path':'path'},5,True,'Creates a new folder; existing folders are left intact',create_dir),
          ('workspace.create_file','Create a new supported UTF-8 text file without overwriting','A',{'path':'path','content':'text'},5,True,'Creates a new file; existing files are never overwritten',create_file),
          ('workspace.edit_file','Replace contents of an existing supported UTF-8 text file','B',{'path':'path','content':'text'},10,False,'Replaces the contents of an existing file',edit_file),
          ('workspace.copy_file','Copy a workspace file without replacing an existing destination','B',{'source':'path','destination':'path'},10,True,'Creates another copy; destination must not exist',copy_file),
          ('workspace.move_file','Move a workspace file without replacing an existing destination','B',{'source':'path','destination':'path'},10,True,'Moves a file within the workspace',move_file),
          ('workspace.rename_file','Rename a workspace file in its current folder','B',{'source':'path','destination':'path'},5,True,'Renames a file; destination must not exist',rename),
          ('workspace.delete_file','Delete one workspace file','C',{'path':'path'},5,False,'Permanently deletes this file; no recycle-bin recovery is provided',delete_file),
        ]
        for spec in specs:self._register(*spec)
        if self.desktop: self._register_desktop_actions()
        if self.browser: self._register_browser_actions()

    def _register_desktop_actions(self):
        d=self.desktop; getcfg=self.config_getter
        def enabled():
            if not getcfg().get('security',{}).get('computer_control_enabled',False): raise PermissionError('Desktop control is disabled in local configuration.')
            if __import__('orbit.adapters.computer',fromlist=['EMERGENCY_STOP']).EMERGENCY_STOP.is_set(): raise PermissionError('Emergency stop is active.')
        def capture(p):
            enabled(); self.screenshot_dir.mkdir(parents=True,exist_ok=True); dest=self.screenshot_dir/'latest.png'
            img=d.screenshot(dest,p.get('region') or None,p.get('scope','screen'),p.get('max_dimension',1280)); o=d.last_observation
            return {'path':'DATA/screenshots/latest.png','width':img.width,'height':img.height,'screen_width':o['screen_width'],'screen_height':o['screen_height'],'observed_at':o['at'],'scope':o['scope'],'verified':dest.is_file(),'summary':f'Captured {o["scope"]} screenshot ({img.width}x{img.height}) at {o["at"]:.3f}.'}
        def active(p): enabled(); return {**d.active_window(),'verified':True,'summary':'Read the active window title and bounds.'}
        def windows(p): enabled(); return d.list_windows()
        def apps(p): enabled(); return d.discover_applications()
        def launch(p):
            enabled(); allowed=getcfg().get('security',{}).get('approved_applications',{}); return d.launch_application(p['app_id'],allowed)
        def activate(p): enabled(); return d.activate_window(p['window_id'],p['observed_at'])
        def closewin(p): enabled(); return d.close_window(p['window_id'],p['observed_at'])
        def click(p): enabled(); d.click(p['x'],p['y'],p['observed_at'],p['button'],p['clicks']); return {'action_sent':True,'verified':False,'summary':f'Sent {p["button"]} click at fresh observed point ({p["x"]},{p["y"]}); the effect has not been observed.'}
        def move(p): enabled(); d.move(p['x'],p['y'],p['observed_at']); return {'action_sent':True,'verified':False,'summary':f'Sent cursor movement to ({p["x"]},{p["y"]}); the resulting desktop state has not been re-observed.'}
        def scroll(p): enabled(); d.scroll(p['amount'],p['x'],p['y'],p['observed_at']); return {'action_sent':True,'verified':False,'summary':f'Sent scroll input at ({p["x"]},{p["y"]}); the effect has not been observed.'}
        def drag(p): enabled(); d.drag(p['x1'],p['y1'],p['x2'],p['y2'],p['observed_at'],p['button']); return {'action_sent':True,'verified':False,'summary':'Sent drag input; the resulting desktop state has not been observed.'}
        def type_text(p): enabled(); d.type_text(p['text']); return {'action_sent':True,'verified':False,'characters':len(p['text']),'summary':'Sent approved text to the focused desktop control; target and result have not been observed.'}
        def key(p): enabled(); d.press_key(p['key']); return {'action_sent':True,'verified':False,'summary':f'Sent allowlisted key {p["key"]}; the resulting state has not been observed.'}
        def hotkey(p): enabled(); d.hotkey(*p['keys']); return {'action_sent':True,'verified':False,'summary':f'Sent approved shortcut {"+".join(p["keys"])}; the resulting state has not been observed.'}
        def clipread(p): enabled(); return d.clipboard_read()
        def clipwrite(p): enabled(); return d.clipboard_write(p['text'])
        specs=[
          ('desktop.capture_screen','Capture full, active-window, or selected-region screenshot','A',{'scope':'str','region':'nullable-list','max_dimension':'int'},8,True,'Reads the current screen and overwrites only DATA/screenshots/latest.png',capture),
          ('desktop.active_window','Read active window title and bounds','A',{},4,True,'Read-only window metadata',active),
          ('desktop.list_windows','List visible windows and titles','A',{},8,True,'Read-only window metadata',windows),
          ('desktop.discover_applications','Discover desktop application shortcuts without launching them','A',{},10,True,'Read-only platform application metadata; discovered apps are not automatically approved',apps),
          ('desktop.launch_approved_app','Launch one user-allowlisted application executable','A',{'app_id':'str'},6,True,'Launches exactly one application configured in security.approved_applications; no arguments or shell',launch),
          ('desktop.activate_window','Activate a recently observed window','B',{'window_id':'str','observed_at':'number'},5,True,'Changes the foreground window based on a recent list/active-window observation',activate),
          ('desktop.close_window','Request window close; save dialogs may appear','C',{'window_id':'str','observed_at':'number'},5,False,'May close an application and risks unsaved changes',closewin),
          ('desktop.move_cursor','Move cursor to a fresh screenshot coordinate','B',{'x':'int','y':'int','observed_at':'number'},5,True,'Moves the pointer; fresh screenshot and bounds required',move),
          ('desktop.click','Click a fresh screenshot coordinate','C',{'x':'int','y':'int','observed_at':'number','button':'str','clicks':'int'},5,False,'Can activate a control or trigger a consequential external action; fresh screenshot required',click),
          ('desktop.scroll','Scroll at a fresh screenshot coordinate','B',{'amount':'int','x':'int','y':'int','observed_at':'number'},5,True,'Changes the active view; amount bounded to 10 wheel ticks',scroll),
          ('desktop.drag','Drag between fresh screenshot coordinates','C',{'x1':'int','y1':'int','x2':'int','y2':'int','observed_at':'number','button':'str'},8,False,'May move or modify desktop content; fresh screenshot required',drag),
          ('desktop.type_text','Type bounded text into the focused desktop control','B',{'text':'text'},8,False,'Types into whatever control has focus; verify target application first',type_text),
          ('desktop.press_key','Press one allowlisted desktop navigation key','C',{'key':'str'},4,False,'May change application state; destructive editing/system keys are denied',key),
          ('desktop.hotkey','Send a short allowlisted keyboard shortcut','C',{'keys':'list'},4,False,'Potentially consequential keyboard shortcut; dangerous/system shortcuts are denied',hotkey),
          ('desktop.clipboard_read','Read clipboard text (sensitive)','C',{},3,True,'Reads up to 2,000 characters of potentially sensitive clipboard data',clipread),
          ('desktop.clipboard_write','Write bounded text to clipboard','B',{'text':'text'},3,True,'Replaces local clipboard contents with the exact approved text',clipwrite),
        ]
        for spec in specs:self._register(*spec)

    def _register_browser_actions(self):
        b=self.browser; stop=__import__('orbit.adapters.computer',fromlist=['EMERGENCY_STOP']).EMERGENCY_STOP
        def check():
            if stop.is_set(): raise PermissionError('Emergency stop is active.')
        def nav(p): check(); return b.navigate(p['url'])
        def read(p): check(); return b.read_page()
        def click(p): check(); return b.click(p['selector'])
        def fill(p): check(); return b.fill(p['selector'],p['text'])
        def press(p): check(); return b.press(p['selector'],p['key'])
        def scroll(p): check(); return b.scroll(p['amount'])
        def shot(p): check(); return b.screenshot()
        def newtab(p): check(); return b.open_tab(p['url'])
        def switch(p): check(); return b.switch_tab(p['index'])
        def submit(p): check(); return b.submit_form(p['selector'],p['expected_confirmation'])
        specs=[
          ('browser.navigate','Navigate to an HTTP/HTTPS page (site content is untrusted)','B',{'url':'str'},20,True,'External website navigation; requires per-step approval',nav),
          ('browser.read_page','Read visible text, links and accessible controls from the current page','A',{},15,True,'Read-only page extraction; extracted content is untrusted and not policy',read),
          ('browser.click','Click a visible browser control using an exact CSS or semantic selector','C',{'selector':'str'},15,False,'May trigger an external action; requires exact per-step approval',click),
          ('browser.fill','Fill one visible non-password browser control; does not submit the form','B',{'selector':'str','text':'text'},15,True,'Enters exact text on a website; passwords and file-upload fields are denied',fill),
          ('browser.press','Send an allowlisted key to a visible browser control','C',{'selector':'str','key':'str'},15,False,'Can submit or change web application state; exact approval required',press),
          ('browser.scroll','Scroll the active page by a bounded amount','B',{'amount':'int'},15,True,'Changes the current website view',scroll),
          ('browser.screenshot','Capture the browser viewport to the USB-local data folder','A',{},15,True,'Reads page pixels; latest screenshot replaces DATA/browser/latest.png',shot),
          ('browser.open_tab','Open a new browser tab at a safe URL','B',{'url':'str'},20,True,'Opens a page in the USB-local browser profile',newtab),
          ('browser.switch_tab','Switch to a tab index','A',{'index':'int'},10,True,'Switches only among existing ORBIT-managed tabs',switch),
          ('browser.submit_form','Submit a selected form and require visible confirmation text','C',{'selector':'str','expected_confirmation':'str'},20,False,'Submits website data; explicit exact approval is required',submit),
        ]
        for spec in specs:self._register(*spec)
