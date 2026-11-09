"""Geometry integration only; all materials and applied loads are synthetic."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import unittest
import numpy as np
from analysis.sponge.geometry import Sponge,SpongeConfig,outward_boundary
from analysis.fem_solver.solver import BlockSolver
from analysis.material.hyperfoam import Hyperfoam


class SpongeTests(unittest.TestCase):
    def test_dimensions_connectivity_and_outward_boundary(self):
        for resolution in [(1,1,1),(2,2,2)]:
            s=Sponge(subdivisions=resolution);v=s.solver.X;c=s.config
            np.testing.assert_allclose(v.min(axis=0),[0,0,.007],atol=1e-16)
            np.testing.assert_allclose(v.max(axis=0),[.073,.05,.027],atol=1e-16)
            np.testing.assert_allclose(np.ptp(v,axis=0),[.073,.05,.02],atol=1e-16)
            self.assertAlmostEqual(s.solver.assembly.reference_volume,.073*.05*.02,places=16)
            self.assertEqual(len(np.unique(v,axis=0)),len(v))
            for cell in s.solver.cells:self.assertGreater(np.linalg.det((v[cell[1:]]-v[cell[0]]).T),0)
            p=v[s.boundary];area=.5*np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0]);center=(v.min(axis=0)+v.max(axis=0))/2
            self.assertTrue(np.all(np.einsum('ij,ij->i',area,p.mean(axis=1)-center)>0))
            np.testing.assert_allclose(area.sum(axis=0),0,atol=1e-17)
            enclosed=np.sum(np.einsum('ij,ij->i',p[:,0],area))/3
            self.assertAlmostEqual(enclosed,c.yellow_volume,places=16)
            np.testing.assert_allclose(v[s.solver.bottom,2],.007,atol=1e-16)
            np.testing.assert_allclose(v[s.solver.top,2],.027,atol=1e-16)

    def test_rigid_backing_platen_and_reference(self):
        s=Sponge();back=s.backing_vertices.copy();c=s.config;r=s.solve_force(0)
        np.testing.assert_allclose(r.positions,s.solver.X,atol=1e-14)
        self.assertLess(abs(r.energy),1e-20)
        np.testing.assert_allclose(np.ptp(back,axis=0),[.073,.05,.007])
        r=s.solve_displacement(.008)
        np.testing.assert_array_equal(back,s.backing_vertices)
        np.testing.assert_allclose(r.positions[s.solver.bottom,2],.007,atol=1e-15)
        np.testing.assert_allclose(r.positions[s.solver.top,2],.019,atol=1e-15)
        np.testing.assert_allclose(np.ptp(s.platen_vertices(.008),axis=0),[.085,.05,0])
        self.assertAlmostEqual(c.contact_area,.00365)
        self.assertNotEqual(c.contact_area,c.platen_width*c.platen_length)
        self.assertAlmostEqual(r.displacement/c.yellow_height,.4)

    def test_force_balance_and_actual_unload(self):
        for beta in [0,.125]:
            s=Sponge(material=Hyperfoam(2000,10,beta));r=s.solve_force(2.)
            self.assertGreater(r.displacement,0)
            self.assertLess(abs(r.top_reaction-2),2e-7)
            self.assertLess(abs(r.bottom_reaction-2),5e-7)
            self.assertLess(r.free_residual,1.01e-8);self.assertGreater(r.min_J,0)
            back=s.backing_vertices.copy();loaded=r.positions.copy()
            result=s.solve_force(0)
            np.testing.assert_allclose(result.positions,s.solver.X,atol=3e-8)
            np.testing.assert_array_equal(loaded,r.positions)
            self.assertIsNot(result,s.solver.cache.get(r.displacement))
            self.assertLess(abs(result.top_reaction),2e-7)
            self.assertLess(abs(result.energy),1e-10)
            np.testing.assert_array_equal(back,s.backing_vertices)
            # Coupled case must relax expanded lateral coordinates, rather than
            # returning an old cached reference object.
            if beta:
                self.assertGreater(result.iterations,0)
                self.assertGreater(len(result.history),1)

    def test_elevated_vs_local_translation(self):
        for beta in [0,.125]:
            m=Hyperfoam(2000,10,beta)
            s=Sponge(material=m);flat=BlockSolver(m,dimensions=(.073,.05,.02),subdivisions=(2,2,2))
            for mode,value in [('d',.006),('force',1.5)]:
                a=s.solve_displacement(value) if mode=='d' else s.solve_force(value)
                b=flat.solve_displacement(value) if mode=='d' else flat.solve_force(value)
                self.assertLess(abs(a.energy-b.energy),1e-10)
                self.assertLess(abs(a.top_reaction-b.top_reaction),2e-7)
                self.assertLess(abs(a.displacement-b.displacement),1e-8)
                np.testing.assert_allclose(a.positions-[0,0,.007],b.positions,atol=3e-8)

    def test_nonzero_beta_and_mesh_consistency(self):
        results=[]
        for subdivisions in [(1,1,1),(2,2,2)]:
            s=Sponge(subdivisions=subdivisions,material=Hyperfoam(2000,10,.125))
            r=s.solve_displacement(.006);F,W,P,*_=s.solver.material.free_uniaxial(.7)
            expected=(s.solver.X-[0,0,.007])@F.T+[0,0,.007]
            np.testing.assert_allclose(r.positions,expected,atol=3e-8)
            self.assertGreater(np.ptp(r.positions,axis=0)[1],.05)
            self.assertLess(abs(r.top_reaction+.00365*P[2,2]),2e-7)
            results.append(r)
        self.assertLess(abs(results[0].top_reaction-results[1].top_reaction),2e-7)
        self.assertLess(abs(results[0].energy-results[1].energy),1e-10)

    def test_invalid_config_and_origin(self):
        with self.assertRaises(ValueError):SpongeConfig(yellow_height=-.02)
        with self.assertRaises(ValueError):Sponge().platen_vertices(.02)
        for origin in [(0,0),(0,0,np.nan),(0,0,1j)]:
            with self.assertRaises(ValueError):BlockSolver(Hyperfoam(2000,10,0),origin=origin)


if __name__=='__main__':unittest.main()
