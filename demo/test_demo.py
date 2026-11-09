"""Frozen workflow and solved-output integrity; synthetic examples stay in temp files."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import csv
import json
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from demo.model import ROOT,configuration,new_sponge,CONDITION
from demo.evaluate import predict,score,write_new


class DemoTests(unittest.TestCase):
    def test_frozen_precision_and_model(self):
        c=configuration();self.assertEqual(c['mu_Pa'],6999.814990181902)
        self.assertEqual((c['alpha'],c['beta']),(10,0))
        self.assertEqual(c['geometry_m']['yellow_height'],.020)
        self.assertEqual(configuration('alpha20')['alpha'],20)

    def test_prediction_before_observation_and_no_refit(self):
        receipt=predict(825.,CONDITION,'SYNTHETIC UNIT TEST ONLY','synthetic-test')
        self.assertAlmostEqual(receipt['force_N'],8.09325)
        self.assertAlmostEqual(receipt['predicted_compression_mm'],7.4884394136,places=5)
        observation=dict(experiment_id='synthetic-test',loading_condition=CONDITION,
                         initial_state_notes='Synthetic fixture, not a new experiment',
                         observed_settled_compression_mm=receipt['predicted_compression_mm']+.5)
        result=score(receipt,observation)
        self.assertAlmostEqual(result['residual_prediction_minus_observation_mm'],-.5)
        altered=dict(receipt,actual_measured_total_bottle_mass_g=900)
        with self.assertRaises(ValueError):score(altered,observation)
        changed=configuration();changed['mu_Pa']+=1
        with patch('demo.evaluate.configuration',return_value=changed):
            with self.assertRaises(ValueError):score(receipt,observation)

    def test_scope_and_exclusive_records(self):
        with self.assertRaises(ValueError):predict(825,'tilted','notes','id')
        with self.assertRaises(ValueError):predict(-1,CONDITION,'notes','id')
        with self.assertRaises(RuntimeError):predict(2000,CONDITION,'notes','id')
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'receipt.json';write_new(p,dict(synthetic=True))
            with self.assertRaises(FileExistsError):write_new(p,dict(synthetic=False))
            self.assertTrue(json.loads(p.read_text())['synthetic'])

    def test_saved_nodes_are_equilibrated_fem_dofs(self):
        s=new_sponge(configuration());data=np.load(ROOT/'demo/outputs/solved_fem_states.npz')
        self.assertEqual(data['positions_m'].shape,(51,27,3))
        np.testing.assert_array_equal(data['cells'],s.solver.cells)
        for force,d,x in zip(data['forces_N'],data['compression_m'],data['positions_m']):
            state=s.solver.assembly.evaluate(x,s.solver.material)
            self.assertGreater(min(e.J for e in state.elements),0)
            self.assertLess(np.max(abs(state.energy_gradient.ravel()[s.solver.free])),5.001e-8)
            self.assertLess(abs(-state.energy_gradient[s.solver.top,2].sum()-force),2e-6)
            np.testing.assert_allclose(x[s.solver.bottom,2],.007,atol=1e-15)
            np.testing.assert_allclose(x[s.solver.top,2],.027-d,atol=1e-15)
        np.testing.assert_allclose(data['positions_m'][-1],data['reference_m'],atol=3e-8)

    def test_real_frame_indices_and_time_labels(self):
        with (ROOT/'demo/outputs/real_frame_manifest.csv').open() as f:manifest=list(csv.DictReader(f))
        self.assertEqual(len(manifest),6)
        for r in manifest:
            with (ROOT/f'analysis/outputs/{r["video"]}/measurements.csv').open() as f:rows=list(csv.DictReader(f))
            source=rows[int(r['frame'])]
            self.assertAlmostEqual(float(source['time_s']),float(r['time_s']),places=6)
            self.assertGreaterEqual(float(r['time_s']),float(r['hold_start_s']))
            self.assertLessEqual(float(r['time_s']),float(r['hold_end_s']))


if __name__=='__main__':unittest.main()
