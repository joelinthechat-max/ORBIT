"""Real-browser acceptance test; requires a compatible browser installed by the operator.
Does not attach to any existing browser profile or endpoint. All pages are local fixtures.
"""
import sys,tempfile,threading,http.server,socketserver
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import orbit
from orbit.adapters.browser import BrowserAdapter
class Fixture(http.server.BaseHTTPRequestHandler):
 def do_GET(self):
  self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.end_headers();self.wfile.write(b'''<!doctype html><title>ORBIT Browser Fixture</title><h1>Local browser adapter test</h1><label for="q">Search query</label><input id="q" aria-label="Search query"><input id="password" type="password"><form id="f" onsubmit="event.preventDefault();document.querySelector('#result').innerText='Saved fixture entry';return false"><input name="title" value="draft"><button type="submit">Save fixture</button></form><button id="advance" onclick="document.body.dataset.state='advanced';document.querySelector('#result').innerText='Advanced state observed'">Advance state</button><button id="dialog" onclick="alert('ORBIT fixture alert')">Show dialog</button><div id="result">Ready</div>''')
 def log_message(self,*args):pass
class Server(socketserver.TCPServer): allow_reuse_address=True

def main():
 s=Server(('127.0.0.1',0),Fixture); threading.Thread(target=s.serve_forever,daemon=True).start()
 with tempfile.TemporaryDirectory(prefix='orbit-browser-qa-') as d:
  cfg={'browser':{'enabled':True,'headless':True,'allow_private_hosts':True,'executable_path':''}}; b=BrowserAdapter(Path(d),lambda:cfg)
  if not b.status()['available']:
   print('SKIP: Playwright package/browser unavailable:',b.status()['reason']); s.shutdown();s.server_close();return 0
  try:
   url=f'http://127.0.0.1:{s.server_address[1]}/'
   nav=b.navigate(url); assert nav['http_status']==200
   page=b.read_page(); assert page['page']['title']=='ORBIT Browser Fixture' and page['untrusted_page_content']
   fill=b.fill('role:textbox:Search query','fixture needle'); assert fill['verified'] and fill['characters']==len('fixture needle')
   try:b.fill('#password','should-not-be-sent')
   except PermissionError:pass
   else:raise AssertionError('password field was not denied')
   click=b.click('role:button:Advance state'); assert click['verified']; assert 'Advanced state observed' in b.read_page()['page']['text']
   try:b.click('role:button:Show dialog')
   except RuntimeError:pass
   else:raise AssertionError('unchanged page after dialog was reported as a verified click')
   dialog=b.read_page()['dialog']; assert dialog and dialog['handled']=='dismissed (safe default)'
   submitted=b.submit_form('form#f','Saved fixture entry'); assert submitted['verified'] and submitted['confirmation']=='Saved fixture entry'
   shot=b.screenshot(); assert shot['verified'] and (Path(d)/'DATA/browser/latest.png').is_file()
   tabs=b.open_tab('about:blank'); assert tabs['url']=='about:blank'; assert b.switch_tab(0)['index']==0
   print('PASS: isolated Chromium session, localhost fixture, page-read, fill (no submission), password denial, observable click, dismissed JavaScript dialog, screenshot, tab open/switch.')
   print('Dialog handled safely:',b.read_page()['dialog'])
  finally:b.close();s.shutdown();s.server_close()
 return 0
if __name__=='__main__':raise SystemExit(main())
