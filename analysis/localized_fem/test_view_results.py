"""Result-viewer data/interaction tests; no localized solve or browser needed."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import numpy as np
from analysis.localized_fem.view_results import build_view

ROOT=Path(__file__).resolve().parents[2]
EXAMPLE=ROOT/'analysis/localized_fem/phase7c/cli_localized'


class ViewerTests(unittest.TestCase):
    def make_example(self,directory):
        for name in ['nodes.csv','boundary_triangles.csv','diagnostics.json','inputs.json']:
            shutil.copyfile(EXAMPLE/name,Path(directory)/name)
        (Path(directory)/'sequence').mkdir()
        shutil.copyfile(EXAMPLE/'sequence/solved_states.npz',Path(directory)/'sequence/solved_states.npz')

    def test_saved_coordinates_are_not_modified(self):
        expected=np.loadtxt(EXAMPLE/'nodes.csv',delimiter=',',skiprows=1)
        digest=hashlib.sha256((EXAMPLE/'nodes.csv').read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory() as directory:
            self.make_example(directory);page=build_view(directory).read_text(encoding='utf-8')
            data=json.loads(re.search(r'<script id="saved-data" type="application/json">(.*?)</script>',page,re.S)[1])
            np.testing.assert_array_equal(data['reference'],expected[:,1:4])
            with np.load(EXAMPLE/'sequence/solved_states.npz') as saved:
                np.testing.assert_array_equal(data['states'],saved['positions'])
                np.testing.assert_array_equal(data['forces'],saved['force_N'])
            self.assertIn('10x (visualization only)',page)
            self.assertNotIn('https://',page)
        self.assertEqual(hashlib.sha256((EXAMPLE/'nodes.csv').read_bytes()).hexdigest(),digest)

    def test_failed_run_has_no_viewer(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):build_view(directory)
            self.assertFalse((Path(directory)/'viewer.html').exists())

    def test_canvas_logic_and_controls(self):
        # Execute JavaScript with a small DOM/canvas test double. This checks
        # syntax, finite projection coordinates, all states, scale and playback;
        # it is not a browser screenshot/visual rendering claim.
        if not shutil.which('node'):self.skipTest('Node unavailable for optional JavaScript check')
        with tempfile.TemporaryDirectory() as directory:
            self.make_example(directory);target=build_view(directory)
            harness=Path(directory)/'check.cjs'
            harness.write_text(r'''
const fs=require('fs'),vm=require('vm');const page=fs.readFileSync(process.argv[2],'utf8');
const blocks=[...page.matchAll(/<script[^>]*>([\s\S]*?)<\/script>/g)].map(x=>x[1]);
const data=JSON.parse(blocks[0]);let lines=0,interval=null;let elements={};
const finite=(...args)=>{for(const a of args)if(typeof a==='number'&&!Number.isFinite(a))throw Error('Nonfinite canvas coordinate');lines++;};
const context=new Proxy({},{get:(o,k)=>o[k]||finite,set:(o,k,v)=>(o[k]=v,true)});
for(const id of ['mesh','state','magnification','reference','scope','status','explanation','animation','play','force','peak','scale','saved-data'])elements[id]={value:id==='magnification'?'1':'0',checked:true,clientWidth:1000,clientHeight:490,textContent:id==='saved-data'?blocks[0]:'',addEventListener(){},getContext:()=>context,setPointerCapture(){}};
const sandbox={document:{getElementById:id=>elements[id]},window:{},devicePixelRatio:1,setInterval:fn=>(interval=fn,1),clearInterval:()=>{interval=null;},console};
vm.createContext(sandbox);vm.runInContext(blocks[1],sandbox);
const expected=Math.max(...data.states.at(-1).map((p,i)=>(data.reference[i][2]-p[2])*1000)).toFixed(3)+' mm';
if(elements.peak.textContent!==expected)throw Error('Wrong true displacement');
elements.magnification.value='10';elements.magnification.onchange();
if(elements.peak.textContent!==expected||elements.scale.textContent!=='10x visual only')throw Error('Display magnification changed physical readout');
for(let i=0;i<2*data.states.length-1;i++){elements.state.value=i;elements.state.oninput();}
elements.play.onclick();interval();elements.play.onclick();
if(lines<10)throw Error('Nothing drawn');console.log('PASS: projection, all states, playback and magnification');
''',encoding='utf-8')
            result=subprocess.run(['node',str(harness),str(target)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_launcher_prints_where_to_view(self):
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'new'
            result=subprocess.run([sys.executable,'-B','-m','analysis.localized_fem.launch','full-face','--force','6.5','--output',str(output)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn('VIEW MODEL:',result.stdout)
            self.assertTrue((output/'viewer.html').is_file())


if __name__=='__main__':unittest.main(verbosity=2)
