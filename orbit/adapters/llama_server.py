"""Optional subprocess manager for a user-supplied llama-server and user-supplied GGUF weights."""
from __future__ import annotations
import os, platform, subprocess, threading, time, urllib.request, json
from pathlib import Path
from urllib.parse import urlparse

class LocalModelManager:
    def __init__(self,root,config_getter,log_dir):
        self.root=Path(root).resolve(); self.config_getter=config_getter; self.log_dir=Path(log_dir); self._lock=threading.RLock(); self._process=None; self._role=None; self._model=''; self._log_handle=None; self._started=0
    def _platform_runtime(self): return self.root/'RUNTIME'/('WINDOWS' if os.name=='nt' else 'LINUX')
    def _inside(self,path,base):
        p=Path(path).expanduser()
        if not p.is_absolute(): p=self.root/p
        p=p.resolve(); b=Path(base).resolve()
        if p!=b and b not in p.parents: raise ValueError(f'Configured path must stay inside {b.relative_to(self.root)}')
        return p
    def _tail(self):
        try:
            self._log_handle.flush(); text=Path(self._log_handle.name).read_text(encoding='utf-8',errors='replace')
            return text[-2500:]
        except Exception: return ''
    def _alive(self): return bool(self._process and self._process.poll() is None)
    def status(self):
        with self._lock:
            return {'managed':True,'running':self._alive(),'role':self._role if self._alive() else None,'model':self._model if self._alive() else None,'pid':self._process.pid if self._alive() else None,'started_at':self._started if self._alive() else None,'log':str(Path(self._log_handle.name).relative_to(self.root)) if self._log_handle else None,'limitation':'llama-server executable and GGUF model weights must be supplied inside the USB folder; only one ORBIT-managed role runs at a time.'}
    def _wait_ready(self,endpoint,proc,timeout=180):
        deadline=time.monotonic()+max(10,min(int(timeout),180)); last='server is loading model'
        while time.monotonic()<deadline:
            if proc.poll() is not None: raise RuntimeError(f'llama-server exited during model load (code {proc.returncode}). {self._tail()}')
            try:
                with urllib.request.urlopen(endpoint.rstrip('/')+'/models',timeout=2) as r: data=json.load(r)
                ids=[x.get('id') for x in data.get('data',[]) if isinstance(x,dict)]
                if ids: return ids
            except Exception as e: last=str(e)
            time.sleep(.5)
        raise TimeoutError(f'llama-server did not become ready within {timeout} seconds: {last}. {self._tail()}')
    def start(self,role,load_timeout=120):
        if role not in {'language','vision'}: raise ValueError('role must be language or vision')
        with self._lock:
            self.stop()
            cfg=self.config_getter().get('models',{}).get(role,{})
            if not cfg.get('enabled'): raise PermissionError(f'{role} model role is disabled in local model configuration')
            if str(cfg.get('backend','')).lower() not in {'llama.cpp','llama.cpp local server','llama-server'}: raise ValueError('Managed loading supports llama.cpp only; keep other compatible loopback servers externally managed.')
            if str(cfg.get('format','')).lower()!='gguf': raise ValueError('llama.cpp launcher requires the model format to be explicitly set to GGUF')
            raw_model=Path(cfg.get('model_path','')).expanduser()
            model=self._inside(raw_model if raw_model.is_absolute() else self.root/'MODELS'/raw_model,self.root/'MODELS')
            if not model.is_file() or model.suffix.lower()!='.gguf': raise FileNotFoundError('A real .gguf model file is required under MODELS/')
            parsed=urlparse(cfg.get('base_url',''))
            if parsed.hostname not in {'127.0.0.1','localhost','::1'} or not parsed.port or not 1024<=parsed.port<=65535: raise ValueError('Model API must use an explicit loopback port 1024-65535')
            rawexe=cfg.get('server_executable','')
            if not isinstance(rawexe,str) or not rawexe.strip(): raise ValueError('Set server_executable to a user-supplied llama-server inside the platform RUNTIME folder')
            raw_exe=Path(rawexe).expanduser()
            if not raw_exe.is_absolute(): raw_exe=self.root/raw_exe if raw_exe.parts and raw_exe.parts[0].upper()=='RUNTIME' else self._platform_runtime()/raw_exe
            exe=self._inside(raw_exe,self._platform_runtime())
            if not exe.is_file(): raise FileNotFoundError(f'User-supplied llama-server not found: {exe}')
            if os.name!='nt' and not os.access(exe,os.X_OK): raise PermissionError('llama-server file is not executable on this Linux filesystem')
            ctx=int(cfg.get('context_tokens',2048)); threads=int(cfg.get('threads',max(1,min(os.cpu_count() or 1,4))))
            if not 512<=ctx<=8192: raise ValueError('context_tokens must be 512-8192 for bounded memory use')
            if not 1<=threads<=32: raise ValueError('threads must be 1-32')
            args=[str(exe),'-m',str(model),'--host','127.0.0.1','--port',str(parsed.port),'-c',str(ctx),'-t',str(threads),'-ngl','0','--alias',str(cfg.get('model') or model.stem)[:80],'--parallel','1']
            if role=='vision':
                mmraw=cfg.get('mmproj_path','')
                if not mmraw: raise ValueError('Vision role requires an explicitly selected compatible mmproj_path under MODELS/')
                raw_mm=Path(mmraw).expanduser(); mm=self._inside(raw_mm if raw_mm.is_absolute() else self.root/'MODELS'/raw_mm,self.root/'MODELS')
                if not mm.is_file() or mm.suffix.lower()!='.gguf': raise FileNotFoundError('Vision multimodal projector must be a real .gguf file under MODELS/')
                args.extend(['--mmproj',str(mm),'--no-mmproj-offload'])
            self.log_dir.mkdir(parents=True,exist_ok=True); log=self.log_dir/f'llama-{role}.log'; self._log_handle=log.open('a',encoding='utf-8')
            try:
                self._process=subprocess.Popen(args,cwd=str(self.root),stdin=subprocess.DEVNULL,stdout=self._log_handle,stderr=subprocess.STDOUT,shell=False,close_fds=(os.name!='nt'))
                self._role=role; self._model=str(model.relative_to(self.root)); self._started=time.time()
                ids=self._wait_ready(cfg['base_url'],self._process,load_timeout)
                expected=str(cfg.get('model') or model.stem)
                if expected not in ids: raise RuntimeError(f'Server ready but served alias {expected!r} was not listed; received {ids!r}')
                return {'started':True,'role':role,'model':expected,'model_ids':ids,'pid':self._process.pid,'endpoint':cfg['base_url'],'verified':True,'summary':f'User-supplied llama.cpp loaded {self._model} on loopback with CPU-only inference.'}
            except Exception:
                self.stop(); raise
    def stop(self,role=None):
        with self._lock:
            if role and self._role and role!=self._role: return {'stopped':False,'reason':f'{self._role} is the active managed role'}
            p=self._process; was=bool(p and p.poll() is None)
            if was:
                p.terminate()
                try: p.wait(timeout=8)
                except subprocess.TimeoutExpired: p.kill(); p.wait(timeout=3)
            self._process=None; self._role=None; self._model=''
            if self._log_handle:
                try: self._log_handle.flush(); self._log_handle.close()
                except Exception: pass
                self._log_handle=None
            return {'stopped':was,'verified':True,'summary':'Stopped the ORBIT-managed local inference process.' if was else 'No ORBIT-managed inference process was running.'}
