"""Run python -B -m unittest discover -s analysis/fem -p test_tetra.py -v."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import unittest
import numpy as np
from analysis.fem.tetra import Tet4,TetAssembly
from analysis.fem.patch_test import SCENARIOS,block_mesh,verify_patch


class ElementTests(unittest.TestCase):
    def setUp(self):
        self.X=np.array([[.001,.002,-.001],[.023,.004,.001],[.005,.019,.002],[.003,.006,.016]])
        self.tet=Tet4(self.X)

    def test_reference_and_geometry(self):
        X=np.array([[0.,0,0],[.02,0,0],[0,.03,0],[0,0,.01]])
        self.assertAlmostEqual(Tet4(X).reference_volume,1e-6,places=18)
        for material in SCENARIOS.values():
            state=self.tet.evaluate(self.X,material)
            np.testing.assert_allclose(state.F,np.eye(3),atol=1e-14)
            self.assertLess(abs(state.energy),1e-24)
            np.testing.assert_allclose(state.P,0,atol=1e-10)
            np.testing.assert_allclose(state.internal_forces,0,atol=1e-13)
        copied=self.tet.reference_positions;copied[:]=0
        np.testing.assert_array_equal(self.tet.reference_positions,self.X)

    def test_translation_and_rotation(self):
        rng=np.random.default_rng(5)
        F=np.array([[.9,.2,.05],[0,1.05,.1],[0,0,.6]])
        for material in SCENARIOS.values():
            x=self.X@F.T;base=self.tet.evaluate(x,material)
            moved=self.tet.evaluate(x+[.04,-.02,.03],material)
            self.assertAlmostEqual(moved.energy/base.energy,1,places=12)
            np.testing.assert_allclose(moved.internal_forces,base.internal_forces,rtol=1e-11,atol=1e-12)
            for _ in range(5):
                R,_=np.linalg.qr(rng.normal(size=(3,3)))
                state=self.tet.evaluate(self.X@R.T,material)
                self.assertLess(abs(state.energy),1e-23)
                np.testing.assert_allclose(state.P,0,atol=1e-9)
                np.testing.assert_allclose(state.internal_forces,0,atol=1e-12)
                rotated=self.tet.evaluate(x@R.T,material)
                self.assertAlmostEqual(rotated.energy/base.energy,1,places=12)
                np.testing.assert_allclose(rotated.internal_forces,base.internal_forces@R.T,rtol=1e-11,atol=1e-12)

    def test_nodal_gradient_and_balance(self):
        for material in SCENARIOS.values():
            for F in [np.diag([1,1,.55]),np.eye(3)*1.1,np.array([[1,.25,.1],[0,1,0],[0,0,.8]])]:
                x=self.X@F.T;state=self.tet.evaluate(x,material);h=2e-8;numeric=np.empty_like(x)
                for a in range(4):
                    for j in range(3):
                        D=np.zeros_like(x);D[a,j]=h
                        numeric[a,j]=(self.tet.evaluate(x+D,material).energy-self.tet.evaluate(x-D,material).energy)/(2*h)
                relative=np.linalg.norm(numeric-state.energy_gradient)/np.linalg.norm(state.energy_gradient)
                self.assertLess(relative,3e-6)
                np.testing.assert_array_equal(state.internal_forces,-state.energy_gradient)
                np.testing.assert_allclose(state.internal_forces.sum(axis=0),0,atol=1e-13)
                torque=np.sum(np.cross(x-x.mean(axis=0),state.internal_forces),axis=0)
                np.testing.assert_allclose(torque,0,atol=1e-14)

    def test_invalid_geometry_and_current_inversion(self):
        material=next(iter(SCENARIOS.values()))
        for bad in [np.zeros((4,3)),self.X[[0,0,2,3]],np.zeros((3,3)),np.full((4,3),np.nan),self.X.astype(complex)]:
            with self.assertRaises(ValueError):Tet4(bad)
        for bad in [self.X[[0,2,1,3]],np.zeros((4,3)),np.full((4,3),np.inf),np.zeros((5,3))]:
            with self.assertRaises(ValueError):self.tet.evaluate(bad,material)
        sliver=np.array([[0,0,0],[1.,0,0],[0,1,0],[0,0,1e-14]])
        with self.assertRaises(ValueError):Tet4(sliver)
        # Consistent odd node permutation changes reference orientation, not physics.
        order=[0,2,1,3];x=self.X@np.diag([.9,1,.6])
        a=self.tet.evaluate(x,material);b=Tet4(self.X[order]).evaluate(x[order],material)
        self.assertEqual(Tet4(self.X[order]).reference_orientation,-self.tet.reference_orientation)
        self.assertAlmostEqual(a.energy,b.energy,places=14)
        np.testing.assert_allclose(b.internal_forces,a.internal_forces[order],rtol=1e-12,atol=1e-13)

    def test_affine_patches_and_mesh_consistency(self):
        for material in SCENARIOS.values():
            for F in [material.free_uniaxial(.6)[0],np.eye(3)*1.12,np.array([[1,.3,0],[0,1,0],[0,0,1.]])]:
                results=[]
                for n,reflection in [(1,False),(2,False),(2,True)]:
                    row,_=verify_patch(n,reflection,material,F);results.append(row)
                self.assertLess(np.ptp([r['energy_J'] for r in results])/results[0]['energy_J'],1e-11)

    def test_nonaffine_assembly_gradient(self):
        X,cells=block_mesh(2);mesh=TetAssembly(X,cells)
        material=SCENARIOS['alpha10_beta0125'];x=X@np.diag([1.02,1.01,.8])
        middle=np.argmin(np.linalg.norm(X-np.array([.015,.01,.005]),axis=1))
        x[middle]+=[.0002,-.0001,.00015]
        state=mesh.evaluate(x,material)
        self.assertGreater(np.linalg.norm(state.internal_forces[middle]),1e-4)
        h=1e-8
        for a in [0,middle,len(X)-1]:
            for j in range(3):
                D=np.zeros_like(x);D[a,j]=h
                numeric=(mesh.evaluate(x+D,material).energy-mesh.evaluate(x-D,material).energy)/(2*h)
                self.assertLess(abs(numeric-state.energy_gradient[a,j]),1e-7)
        np.testing.assert_allclose(state.internal_forces.sum(axis=0),0,atol=1e-12)
        np.testing.assert_allclose(np.sum(np.cross(x,state.internal_forces),axis=0),0,atol=1e-13)

    def test_connectivity_validation(self):
        X,cells=block_mesh()
        for bad in [np.array([[0,1,2,99]]),np.array([[0,0,1,2]]),np.array([[0,1,2,-1]]),cells.astype(float),np.zeros((0,4),int),np.zeros((2,3),int)]:
            with self.assertRaises(ValueError):TetAssembly(X,bad)
        with self.assertRaises(ValueError):TetAssembly(X,cells).evaluate(X[:-1],SCENARIOS['alpha10_beta0'])


if __name__=='__main__':unittest.main()
