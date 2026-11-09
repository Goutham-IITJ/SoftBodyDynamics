"""Tests for split integrity, physical units, exact scaling, and inverse FEM."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import csv
import tempfile
import unittest
import numpy as np
from analysis.calibration.calibrate import (FEMResponse,training_observations,force_from_water,
                                           MAX_COMPRESSION_FRACTION,CALIBRATION_FORCE_TOLERANCE)
from analysis.material.hyperfoam import Hyperfoam
from analysis.sponge.geometry import Sponge


class CalibrationTests(unittest.TestCase):
    def test_mass_units_and_shared_tare(self):
        np.testing.assert_allclose(force_from_water([500,750,1000]),[5.64075,8.09325,10.54575],atol=1e-14)
        for tare in [50,75,100]:
            f=force_from_water([500,750,1000],tare)
            self.assertAlmostEqual(f[1],(f[0]+f[2])/2)
        with self.assertRaises(ValueError):force_from_water(500,-1)

    def test_endpoint_selection_excludes_holdout(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'source.csv'
            rows=[dict(video=v,cycle=c,hold_compression_mm=x) for v,c,x in
                  [('500ml',1,3),('500ml',2,2.5),('750ml',1,999),('750ml',2,-999),('1000ml',1,11),('1000ml',2,10.9)]]
            with path.open('w',newline='') as f:
                w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
            np.testing.assert_allclose(training_observations(path),[.003,.011])
            np.testing.assert_allclose(training_observations(path,(2,2)),[.0025,.0109])

    def test_scaled_response_matches_direct_fem_with_lateral_coupling(self):
        response=FEMResponse(10,.125);mu=7000.;force=8.
        a=response.predict(force,mu)
        direct=Sponge(subdivisions=(1,1,1),material=Hyperfoam(mu,10,.125))
        direct.solver.force_tolerance=CALIBRATION_FORCE_TOLERANCE
        b=direct.solve_force(force)
        np.testing.assert_allclose(a.positions,b.positions,atol=2e-8)
        self.assertLess(abs(a.energy-b.energy),1e-8)
        self.assertLess(abs(a.displacement-b.displacement),2e-9)
        self.assertLess(abs(a.top_reaction-force),2e-6)
        self.assertGreater(a.min_J,0)
        cached=response.sponge.solver.cache[a.displacement]
        self.assertAlmostEqual(a.energy/cached.energy,mu/2000,places=10)

    def test_inverse_recovers_synthetic_direct_scale(self):
        actual=8100.;forces=np.array([4.,9.])
        solid=Sponge(subdivisions=(1,1,1),material=Hyperfoam(actual,10,0))
        observed=np.array([solid.solve_force(f).displacement for f in forces])
        fit=FEMResponse().fit(forces,observed)
        self.assertTrue(fit.success);self.assertLess(abs(fit.mu-actual),.02)
        self.assertLess(fit.rmse_m,2e-9)

    def test_domain_is_not_silently_extended(self):
        response=FEMResponse()
        self.assertEqual(MAX_COMPRESSION_FRACTION,.65)
        self.assertAlmostEqual(response.cap,.013)
        with self.assertRaises(ValueError):response.predict(response.capacity_reference*1.01,2000)
        with self.assertRaises(ValueError):response.fit([5,10],[.003,.014])
        with self.assertRaises(ValueError):response.fit([5,8,10],[.003,.007,.011])
        with self.assertRaises(ValueError):response.predict(1,0)


if __name__=='__main__':unittest.main()
