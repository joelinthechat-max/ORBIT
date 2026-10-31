"""Optional Playwright browser adapter. Pages are untrusted; no webpage text becomes policy."""
from __future__ import annotations
import os, platform, queue, shutil, threading, time, ipaddress
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

SAFE_KEYS={'Enter','Tab','Escape','ArrowUp','ArrowDown','ArrowLeft','ArrowRight','Home','End','PageUp','PageDown','Space'}
ROLE_NAMES={'button','link','textbox','checkbox','radio','tab','menuitem','option','heading','combobox','searchbox'}

class BrowserAdapter:
    def __init__(self,root:Path,config_getter):
        self.root=Path(root).resolve(); self.config_getter=config_getter; self.profile=self.root/'DATA'/'browser'/'profile'; self.downloads=self.root/'DATA'/'browser'/'downloads'
        self._queue=queue.Queue(); self._thread=None; self._ready=threading.Event(); self._start_error=None; self._guard=threading.RLock(); self._running=False; self._page_title=''; self._url=''; self._last_dialog=None; self._pw=None; self._context=None; self._stopping=False

    def _cfg(self): return self.config_getter().get('browser',{})
    def dependency_available(self):
        try:
            from playwright.sync_api import sync_playwright
            return True,None
        except Exception as e: return False,str(e)

    def discover_executable(self):
        cfg=self._cfg(); raw=cfg.get('executable_path','')
        if isinstance(raw,str) and raw.strip():
            p=Path(raw).expanduser()
            if not p.is_absolute(): p=(self.root/p).resolve()
            try:
                if self.root not in p.resolve().parents and p.resolve()!=self.root and p.name.lower() not in {'chrome.exe','msedge.exe','chromium','chromium-browser','google-chrome','google-chrome-stable','chrome'}: return None,'An external browser path must name a recognized Chromium browser executable.'
            except OSError: return None,'Browser executable path is invalid.'
            return (str(p),None) if p.is_file() else (None,'Configured browser executable does not exist.')
        candidates=[]
        if os.name=='nt':
            for env in ('PROGRAMFILES','PROGRAMFILES(X86)','LOCALAPPDATA'):
                base=os.environ.get(env)
                if base:
                    candidates.extend([Path(base)/'Microsoft/Edge/Application/msedge.exe',Path(base)/'Google/Chrome/Application/chrome.exe'])
            candidates.extend([self.root/'RUNTIME'/'WINDOWS'/'browser'/'chrome.exe',self.root/'RUNTIME'/'WINDOWS'/'browser'/'chrome-win64'/'chrome.exe'])
            candidates.extend((self.root/'RUNTIME'/'WINDOWS'/'browser-cache').glob('chromium-*/chrome-win64/chrome.exe'))
        else:
            for name in ('chromium','chromium-browser','google-chrome','google-chrome-stable','chrome'):
                found=shutil.which(name)
                if found: candidates.append(Path(found))
            candidates.extend([self.root/'RUNTIME'/'LINUX'/'browser'/'chrome',self.root/'RUNTIME'/'LINUX'/'browser'/'chrome-linux'/'chrome'])
            candidates.extend((self.root/'RUNTIME'/'LINUX'/'browser-cache').glob('chromium-*/chrome-linux64/chrome'))
        for p in candidates:
            try:
                if p.is_file(): return str(p.resolve()),None
            except OSError: pass
        return None,'No browser executable found. Configure an existing browser or install a compatible Chromium under RUNTIME/<platform>/browser.'

    def status(self):
        dep,dep_error=self.dependency_available(); executable,error=self.discover_executable(); cfg=self._cfg()
        with self._guard:
            running=self._running
        return {'enabled':cfg.get('enabled') is True,'available':bool(dep and executable),'dependency_available':dep,'browser_found':bool(executable),'browser_executable':executable,'headless':bool(cfg.get('headless',False)),'allow_private_hosts':bool(cfg.get('allow_private_hosts',False)),'running':running,'profile':'DATA/browser/profile','downloads':'DATA/browser/downloads','reason':None if dep and executable else (dep_error if not dep else error),'security_note':'Page content is untrusted. Browser controls use fixed DOM queries only; no remote debugging browser is attached.'}

    def _start_worker(self):
        with self._guard:
            if self._thread and self._thread.is_alive(): return
            self._ready.clear(); self._start_error=None; self._stopping=False
            self._thread=threading.Thread(target=self._worker,name='orbit-playwright',daemon=True); self._thread.start()
        if not self._ready.wait(20): raise TimeoutError('Playwright worker startup timed out')
        if self._start_error: raise RuntimeError(self._start_error)

    def _worker(self):
        try:
            from playwright.sync_api import sync_playwright
            self._pw=sync_playwright().start(); self._ready.set()
            while True:
                item=self._queue.get()
                name,params,done,result=item
                try:
                    if name=='__stop':
                        self._close_context(); self._pw.stop(); result['value']={'stopped':True}; done.set(); break
                    result['value']=getattr(self,'_do_'+name)(**params)
                except BaseException as e: result['error']=e
                finally: done.set()
        except BaseException as e:
            self._start_error=f'Playwright could not start: {e}'; self._ready.set()
        finally:
            with self._guard: self._running=False; self._context=None; self._pw=None

    def _submit(self,name,timeout=15,**params):
        cfg=self._cfg()
        if cfg.get('enabled') is not True: raise PermissionError('Browser automation is disabled in CONFIG/orbit.json. Enable it explicitly in the dashboard first.')
        status=self.status()
        if not status['available']: raise RuntimeError(status['reason'] or 'Browser automation is unavailable')
        self._start_worker(); done=threading.Event(); result={}; self._queue.put((name,params,done,result))
        if not done.wait(timeout): raise TimeoutError(f'Browser {name} action exceeded {timeout} seconds')
        if 'error' in result: raise result['error']
        return result.get('value',{})

    def _ensure_context(self):
        if self._context: return
        cfg=self._cfg(); executable,error=self.discover_executable()
        if not executable: raise RuntimeError(error)
        self.profile.mkdir(parents=True,exist_ok=True); self.downloads.mkdir(parents=True,exist_ok=True)
        self._context=self._pw.chromium.launch_persistent_context(user_data_dir=str(self.profile),executable_path=executable,headless=bool(cfg.get('headless',False)),accept_downloads=False,downloads_path=str(self.downloads),viewport={'width':1280,'height':800},locale='en-US',args=['--no-first-run','--no-default-browser-check'])
        self._context.route('**/*',self._route_policy)
        with self._guard: self._running=True
        for page in self._context.pages: self._attach(page)
        self._context.on('page',self._attach)
        if not self._context.pages: self._context.new_page()

    def _route_policy(self,route):
        url=route.request.url
        scheme=urlsplit(url).scheme.lower()
        if scheme not in {'http','https','data','blob','about'} or (scheme=='about' and url!='about:blank'):
            route.abort('blockedbyclient'); return
        if url.startswith(('http://','https://')) and self._cfg().get('allow_private_hosts') is not True:
            host=(urlsplit(url).hostname or '').rstrip('.').lower()
            try:
                private=host in {'localhost','localhost.localdomain'} or not ipaddress.ip_address(host).is_global
            except ValueError: private=host in {'localhost','localhost.localdomain'}
            if private:
                route.abort('blockedbyclient'); return
        route.continue_()

    def _attach(self,page):
        page.on('dialog',self._on_dialog)
    def _on_dialog(self,dialog):
        self._last_dialog={'type':dialog.type,'message':dialog.message[:500],'handled':'dismissed (safe default)','at':time.time()}
        try: dialog.dismiss()
        except Exception: pass
    def _close_context(self):
        if self._context:
            try: self._context.close()
            finally: self._context=None
        with self._guard: self._running=False
    def _page(self,index=None):
        self._ensure_context(); pages=self._context.pages
        if not pages: pages=[self._context.new_page()]
        i=len(pages)-1 if index is None else index
        if type(i) is not int or not 0<=i<len(pages): raise ValueError('Tab index is outside the current tab list')
        return pages[i]
    def _locator(self,page,selector):
        if not isinstance(selector,str) or not selector.strip() or len(selector)>300: raise ValueError('Selector must be 1-300 characters')
        s=selector.strip()
        if s.startswith('role:'):
            pieces=s.split(':',2)
            if len(pieces)!=3 or pieces[1] not in ROLE_NAMES or not pieces[2].strip(): raise ValueError('Semantic selector format is role:<allowed-role>:<exact accessible name>')
            return page.get_by_role(pieces[1],name=pieces[2],exact=True)
        if s.lower().startswith(('javascript:','file:')): raise ValueError('Unsafe selector scheme denied')
        return page.locator(s)
    def _safe_url(self,url):
        if not isinstance(url,str) or len(url)>2048: raise ValueError('URL must be at most 2,048 characters')
        parsed=urlsplit(url.strip())
        if parsed.scheme not in {'http','https'} or not parsed.hostname or parsed.username or parsed.password: raise ValueError('Only credential-free HTTP/HTTPS URLs are allowed')
        if self._cfg().get('allow_private_hosts') is not True:
            host=parsed.hostname.rstrip('.').lower()
            if host in {'localhost','localhost.localdomain'}: raise ValueError('Local/private hosts are denied by default; opt in only for a trusted local web app.')
            try:
                addr=ipaddress.ip_address(host)
                if not addr.is_global: raise ValueError('Local/private/reserved IP addresses are denied by default.')
            except ValueError as e:
                if str(e).startswith('Local/private'): raise
        return urlunsplit((parsed.scheme,parsed.netloc,parsed.path or '/',parsed.query,''))
    @staticmethod
    def _safe_link(url):
        try:
            p=urlsplit(url)
            if p.scheme not in {'http','https'} or not p.hostname: return ''
            return urlunsplit((p.scheme,p.netloc,p.path,'',''))[:1000]
        except Exception: return ''

    def navigate(self,url): return self._submit('navigate',timeout=20,url=self._safe_url(url))
    def read_page(self): return self._submit('read_page',timeout=15)
    def click(self,selector): return self._submit('click',timeout=15,selector=selector)
    def fill(self,selector,text):
        if not isinstance(text,str) or len(text)>2000: raise ValueError('Form text is limited to 2,000 characters')
        return self._submit('fill',timeout=15,selector=selector,text=text)
    def press(self,selector,key):
        if key not in SAFE_KEYS: raise ValueError('Key is outside the safe browser key allowlist')
        return self._submit('press',timeout=15,selector=selector,key=key)
    def scroll(self,amount): return self._submit('scroll',timeout=15,amount=max(-2000,min(int(amount),2000)))
    def screenshot(self): return self._submit('screenshot',timeout=15)
    def open_tab(self,url='about:blank'): return self._submit('open_tab',timeout=20,url=self._safe_url(url) if url!='about:blank' else url)
    def switch_tab(self,index): return self._submit('switch_tab',timeout=10,index=index)
    def submit_form(self,selector,expected_confirmation):
        if not isinstance(expected_confirmation,str) or not expected_confirmation.strip() or len(expected_confirmation)>300: raise ValueError('Provide the visible confirmation text expected after submission')
        return self._submit('submit_form',timeout=20,selector=selector,expected_confirmation=expected_confirmation)
    def close(self):
        with self._guard: alive=bool(self._thread and self._thread.is_alive())
        if not alive: return {'stopped':False}
        done=threading.Event(); result={}; self._queue.put(('__stop',{},done,result)); done.wait(10); return result.get('value',{'stopped':False})

    def _do_navigate(self,url):
        page=self._page(); response=page.goto(url,wait_until='domcontentloaded',timeout=12000); page.wait_for_timeout(150)
        status=response.status if response else 0
        if status>=400: raise RuntimeError(f'Navigation returned HTTP {status}; inspect the error page before continuing')
        self._url=page.url; self._page_title=page.title()[:300]
        return {'url':page.url,'title':self._page_title,'http_status':status,'verified':True,'summary':f'Loaded {page.url} (HTTP {status or "no response status"}).'}

    def _do_read_page(self):
        page=self._page()
        # Fixed read-only DOM query. Page strings are untrusted data and are never treated as system policy.
        data=page.evaluate("""() => {
          const visible=e=>{const r=e.getBoundingClientRect(),s=getComputedStyle(e);return r.width>0&&r.height>0&&s.visibility!=='hidden'&&s.display!=='none'};
          const clean=u=>{try{const x=new URL(u,location.href);return ['http:','https:'].includes(x.protocol)?x.origin+x.pathname:''}catch{return ''}};
          const links=[...document.querySelectorAll('a[href]')].filter(visible).slice(0,100).map(e=>({text:(e.innerText||e.getAttribute('aria-label')||'').trim().slice(0,200),href:clean(e.href)}));
          const controls=[...document.querySelectorAll('button,input,textarea,select,[role=button],[role=link]')].filter(visible).slice(0,100).map(e=>({tag:e.tagName.toLowerCase(),type:(e.type||'').slice(0,30),label:(e.getAttribute('aria-label')||e.labels?.[0]?.innerText||e.getAttribute('placeholder')||e.innerText||'').trim().slice(0,200),disabled:!!e.disabled}));
          return {title:document.title,url:location.href,text:(document.body?.innerText||'').slice(0,20000),links,controls};
        }""")
        data['url']='about:blank' if data.get('url')=='about:blank' else self._safe_url(data['url']); data['title']=str(data.get('title',''))[:300]; data['text']=str(data.get('text',''))[:20000]
        return {'page':data,'dialog':self._last_dialog,'untrusted_page_content':True,'verified':True,'summary':f'Read visible text and {len(data["links"])} links from {data["url"]}; page content is untrusted.'}

    def _do_click(self,selector):
        page=self._page(); loc=self._locator(page,selector); loc.first.wait_for(state='visible',timeout=5000)
        before=(page.url,page.title(),page.locator('body').inner_text(timeout=3000)[:2000],len(self._context.pages))
        loc.first.click(timeout=6000); page.wait_for_timeout(250)
        after=(page.url,page.title(),page.locator('body').inner_text(timeout=3000)[:2000],len(self._context.pages))
        if after==before: raise RuntimeError('Click was sent but no observable URL/title/text/tab change was detected; do not repeat it blindly.')
        return {'url':page.url,'title':page.title()[:300],'dialog':self._last_dialog,'verified':True,'summary':'Browser click caused an observable page/tab state change; inspect the resulting page.'}

    def _do_fill(self,selector,text):
        page=self._page(); loc=self._locator(page,selector).first; loc.wait_for(state='visible',timeout=5000)
        meta=loc.evaluate('(e)=>({type:(e.type||"").toLowerCase(),name:(e.name||"").toLowerCase(),autocomplete:(e.autocomplete||"").toLowerCase()})')
        if meta['type']=='password' or 'password' in meta['autocomplete'] or meta['type']=='file': raise PermissionError('Password and file-upload fields are denied; ORBIT never supplies credentials or local files.')
        loc.fill(text,timeout=6000)
        actual=loc.input_value(timeout=3000)
        if actual!=text: raise RuntimeError('Browser form value did not match the requested text')
        return {'selector':selector,'characters':len(text),'verified':True,'summary':f'Filled the visible non-password control ({len(text)} characters). No form was submitted.'}

    def _do_press(self,selector,key):
        page=self._page(); loc=self._locator(page,selector).first; loc.wait_for(state='visible',timeout=5000); loc.press(key,timeout=6000)
        return {'url':page.url,'verified':True,'summary':f'Sent allowlisted key {key} to the selected control; inspect the resulting page.'}

    def _do_scroll(self,amount):
        page=self._page(); before=page.evaluate('window.scrollY'); page.mouse.wheel(0,amount); page.wait_for_timeout(150); after=page.evaluate('window.scrollY')
        return {'scroll_y_before':before,'scroll_y_after':after,'verified':True,'summary':f'Scrolled browser page by {amount} pixels.'}

    def _do_screenshot(self):
        page=self._page(); dest=self.root/'DATA'/'browser'/'latest.png'; dest.parent.mkdir(parents=True,exist_ok=True); page.screenshot(path=str(dest),full_page=False,animations='disabled')
        return {'path':'DATA/browser/latest.png','url':page.url,'title':page.title()[:300],'verified':dest.is_file(),'summary':'Captured and saved the current browser viewport on the USB workspace.'}

    def _do_open_tab(self,url):
        self._ensure_context(); page=self._context.new_page(); page.goto(url,wait_until='domcontentloaded',timeout=12000) if url!='about:blank' else None
        return {'index':len(self._context.pages)-1,'url':page.url,'title':page.title()[:300],'verified':True,'summary':f'Opened browser tab {len(self._context.pages)-1}.'}

    def _do_switch_tab(self,index):
        page=self._page(index); page.bring_to_front(); return {'index':index,'url':page.url,'title':page.title()[:300],'verified':True,'summary':f'Switched to browser tab {index}.'}

    def _do_submit_form(self,selector,expected_confirmation):
        page=self._page(); form=self._locator(page,selector).first; form.wait_for(state='visible',timeout=5000)
        if form.evaluate('(e)=>e.tagName.toLowerCase()')!='form': raise ValueError('submit_form selector must identify a form element')
        form.evaluate('(e)=>e.requestSubmit()'); page.wait_for_load_state('domcontentloaded',timeout=10000)
        confirmation=page.get_by_text(expected_confirmation,exact=False).first
        try: confirmation.wait_for(state='visible',timeout=3000); visible=True
        except Exception: visible=False
        if not visible: raise RuntimeError('Form submit was sent, but expected confirmation text was not observed; inspect manually and do not repeat.')
        return {'url':page.url,'confirmation':expected_confirmation,'verified':True,'summary':'Observed the requested visible confirmation text after submission.'}
