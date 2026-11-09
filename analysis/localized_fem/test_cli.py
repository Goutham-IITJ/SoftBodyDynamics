"""Packaging and exported equilibrium checks; no experimental re-solves."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import numpy as np
from analysis.localized_fem.support import UnilateralSolver
from analysis.localized_fem.traction import Rectangle,integrate_rectangle

ROOT=Path(__file__).resolve().parents[2]
OUTPUT=ROOT/'analysis/localized_fem/phase7c'


class CliTests(unittest.TestCase):
    def run_cli(self,*args):
        return subprocess.run([sys.executable,'-B','-m','analysis.localized_fem.simulator',*map(str,args)],cwd=ROOT,capture_output=True,text=True)

    def test_help_and_invalid_inputs(self):
        self.assertEqual(self.run_cli('--help').returncode,0)
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'invalid'
            r=self.run_cli('full-face','--force','-1','--output',target)
            self.assertNotEqual(r.returncode,0);self.assertFalse(target.exists())
            r=self.run_cli('full-face','--force','1','--output',directory)
            self.assertNotEqual(r.returncode,0)

    def test_timeout_no_solution_export(self):
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'timeout'
            r=self.run_cli('localized','--force','.3','--patch-length-mm','20','--patch-width-mm','30','--center-x-mm','18.25','--center-y-mm','25','--mesh','2','2','1','--time-limit-s','.000001','--output',target)
            self.assertNotEqual(r.returncode,0)
            self.assertTrue((target/'failure.json').is_file())
            self.assertFalse((target/'nodes.csv').exists())

    def test_saved_localized_sequence_kkt(self):
        folder=OUTPUT/'cli_localized';s=UnilateralSolver()
        data=np.load(folder/'sequence/solved_states.npz')
        for x,force in zip(data['positions'],data['force_N']):
            st=s.assembly.evaluate(x,s.material)
            f=integrate_rectangle(s.X,s.top_faces,Rectangle(.01825,.025,.02,.03),force).nodal_forces_N
            residual=st.energy_gradient-f;gap=x[s.bottom,2]-s.origin[2]
            active=s.bottom[gap<=s.gap_tolerance_m]
            free=np.setdiff1d(np.arange(s.X.size),[3*i+2 for i in active]+[3*i+a for i,a in s.anchors])
            self.assertGreaterEqual(gap.min(),-s.gap_tolerance_m)
            self.assertGreaterEqual(residual[active,2].min(),-s.force_tolerance)
            self.assertLessEqual(abs(residual.ravel()[free]).max(),s.force_tolerance)
            self.assertTrue(all(e.J>0 for e in st.elements))
        manifest=json.loads((folder/'sequence/frames.json').read_text())['frames']
        self.assertEqual(len(manifest),9)
        for row in manifest:self.assertEqual(row['force_N'],float(data['force_N'][row['solved_state']]))

    def test_saved_fullface_example(self):
        d=json.loads((OUTPUT/'cli_fullface/diagnostics.json').read_text())
        self.assertAlmostEqual(d['compression_mm'],5.1035044458,places=7)
        self.assertLess(d['force_balance_N'],2e-6)
        self.assertLess(d['free_residual_N'],5e-8)


if __name__=='__main__':unittest.main(verbosity=2)
