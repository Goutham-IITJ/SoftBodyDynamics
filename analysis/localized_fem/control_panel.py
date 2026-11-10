"""Loopback-only force controls for the existing FEM CLI. No new mechanics."""
import argparse
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
import secrets
import subprocess
import sys
import threading
import time
from urllib.parse import unquote,urlsplit
import uuid
import webbrowser
from analysis.localized_fem.view_results import build_view

ROOT=Path(__file__).resolve().parents[2]


class Panel:
    def __init__(self,output,mesh=(2,2,1)):
        self.output=Path(output).resolve();self.output.mkdir(parents=True,exist_ok=True)
        self.mesh=tuple(mesh);self.token=secrets.token_urlsafe(24)
        self.lock=threading.Lock();self.jobs={};self.state=dict(status='idle')

    def submit(self,payload):
        if not isinstance(payload,dict) or set(payload)-{'force','mode','sequence'}:raise ValueError('Unsupported inputs')
        mode=payload.get('mode');force=payload.get('force');sequence=payload.get('sequence',False)
        if mode not in ['full-face','localized']:raise ValueError('Choose full-face or localized')
        if isinstance(force,bool) or not isinstance(force,(int,float)) or not 0<=force<=20:raise ValueError('Force must be finite and between 0 and 20 N (interface guard, not a validated model range)')
        if not isinstance(sequence,bool):raise ValueError('Sequence must be true or false')
        with self.lock:
            if self.state['status']=='running':raise RuntimeError('A solve is already running')
            job=uuid.uuid4().hex;directory=self.output/job;self.jobs[job]=directory
            self.state=dict(status='running',job=job,force=force,mode=mode,started=time.time())
        threading.Thread(target=self.solve,args=(job,directory,mode,force,sequence),daemon=True).start()
        return job

    def solve(self,job,directory,mode,force,sequence):
        cmd=[sys.executable,'-B','-m','analysis.localized_fem.simulator',mode,'--force',str(force),'--output',str(directory)]
        if mode=='localized':cmd+=['--patch-length-mm','20','--patch-width-mm','30','--center-x-mm','18.25','--center-y-mm','25','--mesh',*map(str,self.mesh),'--support','unilateral','--time-limit-s','180']
        if sequence:cmd+=['--sequence']
        try:
            result=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,timeout=210)
            directory.mkdir(exist_ok=True)
            (directory/'console.log').write_bytes((result.stdout+result.stderr).encode('utf-8'))
            if result.returncode:
                failure=directory/'failure.json'
                reason=json.loads(failure.read_text())['reason'] if failure.exists() else 'CLI rejected or failed this request; see console.log'
                raise ValueError(reason)
            viewer=build_view(directory)
            # Keep offline viewer instructions accurate when embedded in a live
            # panel: the controls above, rather than a new CLI command, solve.
            page=viewer.read_text(encoding='utf-8').replace('To change force, patch or mesh, rerun the Python CLI into a new output directory. No solver runs in this browser.',
                'Use the force controls above and Solve &amp; show result to request another Python solve. This embedded mesh view only displays the returned solution.')
            viewer.write_bytes(page.encode('utf-8'))
            diagnostics=json.loads((directory/'diagnostics.json').read_text())
            state=dict(status='converged',job=job,force=force,mode=mode,url=f'/results/{job}/viewer.html',diagnostics=diagnostics)
        except subprocess.TimeoutExpired:
            directory.mkdir(exist_ok=True)
            (directory/'panel_failure.json').write_text(json.dumps(dict(status='failed',reason='210 s process budget reached; no result displayed')))
            state=dict(status='failed',job=job,force=force,mode=mode,error='210 s process budget reached. No result displayed.')
        except Exception as exc:
            state=dict(status='failed',job=job,force=force,mode=mode,error=str(exc))
        with self.lock:self.state=state

    def snapshot(self):
        with self.lock:return self.state.copy()


def make_server(panel,port=0):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass

        def send(self,status,value,kind='application/json'):
            raw=json.dumps(value).encode() if kind=='application/json' else value
            self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(raw)))
            self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(raw)

        def valid_host(self):return self.headers.get('Host')==f'127.0.0.1:{self.server.server_port}'

        def do_GET(self):
            if not self.valid_host():return self.send(403,dict(error='Loopback host only'))
            path=unquote(urlsplit(self.path).path)
            if path=='/':
                page=PAGE.replace('__TOKEN__',panel.token).replace('__MESH__',' x '.join(map(str,panel.mesh)))
                return self.send(200,page.encode(),'text/html; charset=utf-8')
            if path=='/api/status':return self.send(200,panel.snapshot())
            parts=path.split('/')
            if len(parts)>=4 and parts[1]=='results' and parts[2] in panel.jobs:
                base=panel.jobs[parts[2]];target=(base/'/'.join(parts[3:])).resolve()
                if target.is_relative_to(base) and target.is_file() and target.suffix in ['.html','.png','.gif','.json','.csv','.npz']:
                    return self.send(200,target.read_bytes(),mimetypes.guess_type(target.name)[0] or 'application/octet-stream')
            self.send(404,dict(error='Not found'))

        def do_POST(self):
            origin=f'http://127.0.0.1:{self.server.server_port}'
            if not self.valid_host() or self.headers.get('Origin',origin)!=origin or self.headers.get('X-Panel-Token')!=panel.token:
                return self.send(403,dict(error='Only this local panel may start a solve'))
            if self.path!='/api/solve':return self.send(404,dict(error='Not found'))
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=4096:raise ValueError('Invalid request size')
                payload=json.loads(self.rfile.read(length));job=panel.submit(payload)
            except (ValueError,TypeError) as exc:return self.send(400,dict(error=str(exc)))
            except RuntimeError as exc:return self.send(409,dict(error=str(exc)))
            self.send(202,dict(job=job,status='running'))
    return ThreadingHTTPServer(('127.0.0.1',port),Handler)


PAGE='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SoftBodyDynamics | Force controls</title>
<style>body{font:16px/1.5 system-ui;background:#edf2f7;color:#182b3d;margin:0}main{max-width:1250px;margin:auto;padding:22px}.panel{background:white;padding:18px;border-radius:10px;margin-bottom:14px}h1{margin:0}input,select,button{font:inherit;padding:7px}button{background:#145b8c;color:white;border:0;border-radius:5px;cursor:pointer}button:disabled{opacity:.5;cursor:wait}.controls{display:flex;flex-wrap:wrap;align-items:center;gap:16px}input[type=number]{width:100px}input[type=range]{width:220px}iframe{width:100%;height:1100px;border:0;background:white;border-radius:10px}.note{color:#52667b}#message{font-weight:600}label{display:inline-block}</style>
<main><div class="panel"><h1>SoftBodyDynamics: force controls</h1><p>Choose a force, then click <b>Solve &amp; show result</b>. A real Python FEM solve runs locally; moving a control does not stretch the previous result.</p>
<form id="controls" class="controls"><label>Model <select id="mode"><option value="localized">Experimental localized patch</option><option value="full-face">Primary full-face model</option></select></label><label>Requested force (N) <input id="force" type="number" min="0" max="20" step="0.05" value="0.3" required></label><input id="range" aria-label="Requested force" type="range" min="0" max="1" step="0.05" value="0.3"><label>Slider maximum (N) <input id="maximum" type="number" min="0.05" max="20" step="0.05" value="1"></label><label><input id="sequence" type="checkbox"> Include equilibrium playback (slower)</label><button id="solve" type="submit">Solve &amp; show result</button></form>
<p id="geometry" class="note">Localized patch: 20 x 30 mm, center (18.25,25) mm; mesh __MESH__; unilateral bottom support. No rigid-card contact.</p>
<p class="note">Start with 0.3 N or 0.6 N. No reliable maximum localized force is established; larger requests may fail. The separate nominal 10.54575 N prediction already failed. The 20 N interface guard is not a validated force range. No stiffness refit or physics change.</p>
<p id="message" role="status">No solve requested yet. Your saved results are not overwritten. Keep the terminal running; Ctrl+C stops this panel.</p></div>
<iframe id="result" title="Latest converged FEM result" hidden></iframe></main><script>
const force=document.getElementById('force'),range=document.getElementById('range'),maximum=document.getElementById('maximum'),mode=document.getElementById('mode'),button=document.getElementById('solve'),message=document.getElementById('message'),frame=document.getElementById('result');let poll=null,busy=false;
force.oninput=()=>{if(Number(force.value)>Number(range.max)){range.max=force.value;maximum.value=force.value;}range.value=force.value;};range.oninput=()=>force.value=range.value;
maximum.onchange=()=>{if(Number(maximum.value)>0&&Number(maximum.value)<=20){range.max=maximum.value;range.value=Math.min(Number(force.value),Number(range.max));force.value=range.value;}};
mode.onchange=()=>{force.value=mode.value==='full-face'?'6.5':'0.3';range.max=mode.value==='full-face'?'10':'1';maximum.value=range.max;range.value=force.value;document.getElementById('geometry').textContent=mode.value==='full-face'?'Frozen full-face platen, Stage 6 geometry and material unchanged. Compression search limit: 13 mm.':'Localized patch: 20 x 30 mm, center (18.25,25) mm; mesh __MESH__; unilateral bottom support. No rigid-card contact.';};
function finish(){clearInterval(poll);poll=null;busy=false;button.disabled=false;}
async function check(){try{const response=await fetch('/api/status');if(!response.ok)throw Error('Local server is unavailable');const s=await response.json();if(s.status==='running'){message.textContent='Solving '+s.force+' N ('+s.mode+')... this may take seconds or minutes. The force control is a request, not a solved state.';return;}if(s.status==='converged'){finish();frame.src=s.url;frame.hidden=false;message.textContent='CONVERGED: displaying newly solved '+s.force+' N '+s.mode+' result. Files saved as job '+s.job+'.';}else if(s.status==='failed'){finish();frame.hidden=true;frame.removeAttribute('src');message.textContent='FAILED at '+s.force+' N: '+s.error+' No new solution is displayed. Try a smaller request; do not treat failure as a prediction.';}}catch(e){finish();message.textContent=e.message+'. Check that the Python terminal is still running.';}}
document.getElementById('controls').onsubmit=async e=>{e.preventDefault();if(busy)return;busy=true;button.disabled=true;frame.hidden=true;message.textContent='Submitting force request...';try{const r=await fetch('/api/solve',{method:'POST',headers:{'Content-Type':'application/json','X-Panel-Token':'__TOKEN__'},body:JSON.stringify({force:Number(force.value),mode:mode.value,sequence:document.getElementById('sequence').checked})});const s=await r.json();if(!r.ok)throw Error(s.error);poll=setInterval(check,1000);check();}catch(e){finish();message.textContent=e.message;}};
</script></html>'''


def main():
    p=argparse.ArgumentParser(description='Local force-control window backed by the unchanged FEM CLI. Only listens on 127.0.0.1.')
    p.add_argument('--open',action='store_true');p.add_argument('--port',type=int,default=0)
    p.add_argument('--output-root',type=Path,default=ROOT/'runs/interactive')
    p.add_argument('--mesh',type=int,nargs=3,default=(2,2,1),help='Localized mesh for this session; x/y must be positive even integers')
    args=p.parse_args()
    if not 0<=args.port<=65535:p.error('Port must be 0..65535')
    if any(n<1 for n in args.mesh) or args.mesh[0]%2 or args.mesh[1]%2:p.error('Mesh needs positive counts and even x/y')
    panel=Panel(args.output_root,args.mesh);server=make_server(panel,args.port)
    url=f'http://127.0.0.1:{server.server_port}/'
    print(f'Force control panel: {url}\nOutputs: {panel.output}\nKeep this terminal open. Ctrl+C to stop.',flush=True)
    if args.open:webbrowser.open(url)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()


if __name__=='__main__':main()
