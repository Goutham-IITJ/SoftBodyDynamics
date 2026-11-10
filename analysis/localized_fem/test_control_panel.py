"""Loopback panel integration: actual modest solves plus request isolation."""
import json
import shutil
from pathlib import Path
import subprocess
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request,urlopen
from analysis.localized_fem.control_panel import Panel,make_server,PAGE


class PanelTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory();self.panel=Panel(self.temporary.name)
        self.server=make_server(self.panel);self.url=f'http://127.0.0.1:{self.server.server_port}'
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()

    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join();self.temporary.cleanup()

    def request(self,path,body=None,headers=None):
        headers=headers or {}
        if body is not None:headers={'Content-Type':'application/json','X-Panel-Token':self.panel.token,**headers}
        request=Request(self.url+path,data=None if body is None else json.dumps(body).encode(),headers=headers)
        with urlopen(request,timeout=10) as response:return response.status,response.read()

    def wait(self):
        end=time.monotonic()+60
        while time.monotonic()<end:
            state=json.loads(self.request('/api/status')[1])
            if state['status']!='running':return state
            time.sleep(.05)
        self.fail('Test solve exceeded 60 s')

    def test_invalid_requests_and_origin(self):
        for body in [dict(mode='localized',force=-1),dict(mode='localized',force=float('nan')),dict(mode='localized',force=True),dict(mode='bad',force=.3),dict(mode='localized',force=.3,output='outside')]:
            with self.assertRaises(HTTPError) as caught:self.request('/api/solve',body)
            self.assertEqual(caught.exception.code,400)
        for headers in [{'Origin':'https://unrelated.example'},{'X-Panel-Token':'wrong'}]:
            with self.assertRaises(HTTPError) as caught:self.request('/api/solve',dict(mode='localized',force=.3),headers)
            self.assertEqual(caught.exception.code,403)
        with self.assertRaises(HTTPError):self.request('/results/unregistered/../../README.md')
        self.assertEqual(list(Path(self.temporary.name).iterdir()),[])

    def test_fullface_actual_solve_and_result(self):
        self.assertIn(b'Solve &amp; show result',self.request('/')[1])
        self.assertEqual(self.request('/api/solve',dict(mode='full-face',force=6.5))[0],202)
        state=self.wait();self.assertEqual(state['status'],'converged',state)
        self.assertAlmostEqual(state['diagnostics']['compression_mm'],5.1035044458,places=7)
        page=self.request(state['url'])[1]
        self.assertIn(b'saved-data',page)
        self.assertIn(b'Use the force controls above',page)
        self.assertTrue((self.panel.jobs[state['job']]/'nodes.csv').is_file())

    def test_localized_actual_solve(self):
        self.request('/api/solve',dict(mode='localized',force=.3))
        state=self.wait();self.assertEqual(state['status'],'converged',state)
        d=state['diagnostics'];self.assertLessEqual(d['free_residual_N'],5e-8)
        self.assertGreaterEqual(d['min_bottom_gap_m'],-1e-10)
        self.assertGreaterEqual(d['min_contact_reaction_N'],-5e-8)
        self.assertGreater(d['min_J'],0)

    def test_failure_and_busy_no_fake_result(self):
        started=threading.Event();release=threading.Event()
        def fake_run(cmd,**kwargs):
            started.set();release.wait(5)
            directory=Path(cmd[cmd.index('--output')+1]);directory.mkdir()
            (directory/'failure.json').write_text(json.dumps(dict(reason='Synthetic test failure')))
            return subprocess.CompletedProcess(cmd,1,'','failure')
        with patch('analysis.localized_fem.control_panel.subprocess.run',side_effect=fake_run):
            self.request('/api/solve',dict(mode='localized',force=.3));self.assertTrue(started.wait(2))
            with self.assertRaises(HTTPError) as caught:self.request('/api/solve',dict(mode='full-face',force=6.5))
            self.assertEqual(caught.exception.code,409)
            release.set();state=self.wait()
        self.assertEqual(state['status'],'failed');self.assertNotIn('url',state)
        self.assertFalse((self.panel.jobs[state['job']]/'viewer.html').exists())

    def test_slider_and_solve_button_logic(self):
        if not shutil.which('node'):self.skipTest('Node unavailable for optional UI logic test')
        page=Path(self.temporary.name)/'panel.html';page.write_text(PAGE,encoding='utf-8')
        script=Path(self.temporary.name)/'panel.cjs'
        script.write_text(r'''
const fs=require('fs'),vm=require('vm');const html=fs.readFileSync(process.argv[2],'utf8'),js=html.match(/<script>([\s\S]*?)<\/script>/)[1];
let elements={},timer=null,requests=[],failed=false;
for(const id of ['force','range','maximum','mode','solve','message','result','geometry','controls','sequence'])elements[id]={value:({force:'.3',range:'.3',maximum:'1',mode:'localized'})[id]||'',max:'1',checked:false,hidden:true,removeAttribute(name){delete this[name];}};
const context={document:{getElementById:id=>elements[id]},setInterval:fn=>(timer=fn,1),clearInterval:()=>timer=null,fetch:async(path,opts)=>{requests.push({path,opts});return {ok:true,json:async()=>path==='/api/solve'?{job:'test',status:'running'}:failed?{status:'failed',force:.6,error:'Synthetic failure'}:{status:'converged',force:.6,mode:'localized',job:'test',url:'/results/test/viewer.html'}};}};
vm.createContext(context);vm.runInContext(js,context);
(async()=>{
elements.range.value='.6';elements.range.oninput();if(elements.force.value!=='.6')throw Error('Slider not synchronized');
elements.maximum.value='.4';elements.maximum.onchange();if(Number(elements.force.value)!==.4)throw Error('Range clamp not synchronized');
elements.mode.value='full-face';elements.mode.onchange();if(elements.force.value!=='6.5')throw Error('Mode default wrong');
elements.mode.value='localized';elements.mode.onchange();elements.force.value='.6';elements.force.oninput();
await elements.controls.onsubmit({preventDefault(){}});await new Promise(setImmediate);
const sent=JSON.parse(requests.find(r=>r.path==='/api/solve').opts.body);if(sent.force!==.6||sent.mode!=='localized')throw Error('Wrong force request');
if(elements.result.hidden||elements.result.src!=='/results/test/viewer.html')throw Error('Solved viewer not displayed');
failed=true;await elements.controls.onsubmit({preventDefault(){}});await new Promise(setImmediate);
if(!elements.result.hidden||elements.result.src||!elements.message.textContent.includes('FAILED'))throw Error('Failure shows a stale model');
console.log('PASS: slider, range, mode, solve request, returned view and failure state');
})().catch(e=>{console.error(e);process.exitCode=1;});
''',encoding='utf-8')
        result=subprocess.run(['node',str(script),str(page)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)


if __name__=='__main__':unittest.main(verbosity=2)
