"""Lifecycle test using a fake OpenAI-compatible server; does not load model weights or perform inference."""
import sys,tempfile,subprocess,time,json,urllib.request
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from orbit.adapters.llama_server import LocalModelManager

def main():
 if sys.platform=='win32':
  print('SKIP: fake POSIX shebang wrapper is Linux-only; Windows manager not executed in this environment');return 0
 with tempfile.TemporaryDirectory(prefix='orbit-model-manager-') as tmp:
  root=Path(tmp); runtime=root/'RUNTIME/LINUX';runtime.mkdir(parents=True);models=root/'MODELS';models.mkdir();logs=root/'LOGS';
  executable=runtime/'fake-llama-server';executable.write_text('''#!/usr/bin/env python3\nimport argparse,json\nfrom http.server import BaseHTTPRequestHandler,HTTPServer\np=argparse.ArgumentParser();p.add_argument('-m');p.add_argument('--host');p.add_argument('--port',type=int);p.add_argument('-c');p.add_argument('-t');p.add_argument('-ngl');p.add_argument('--alias');p.add_argument('--parallel');a=p.parse_args()\nclass H(BaseHTTPRequestHandler):\n def do_GET(self):\n  b=json.dumps({'data':[{'id':a.alias}]}).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)\n def log_message(self,*args):pass\nHTTPServer((a.host,a.port),H).serve_forever()\n''');executable.chmod(0o755)
  (models/'fixture.gguf').write_bytes(b'not model weights; path-validation fixture only');cfg={'models':{'language':{'enabled':True,'backend':'llama.cpp','format':'GGUF','model_path':'fixture.gguf','base_url':'http://127.0.0.1:19998/v1','model':'fixture-alias','server_executable':'fake-llama-server','context_tokens':512,'threads':1}}}
  manager=LocalModelManager(root,lambda:cfg,logs)
  try:
   started=manager.start('language',load_timeout=10);assert started['verified'] and started['model_ids']==['fixture-alias'];assert manager.status()['running'];stopped=manager.stop();assert stopped['stopped'] and not manager.status()['running'];print('PASS: user-configured USB-contained executable/fixture GGUF validated; fake llama-server spawned without shell on loopback; exact alias detected; managed process stopped cleanly. No inference/model was used.')
  finally:manager.stop()
 return 0
if __name__=='__main__':raise SystemExit(main())
