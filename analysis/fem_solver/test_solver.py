"""Synthetic verification; no experimental inputs."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from dataclasses import replace
import unittest
import numpy as np
from scipy.optimize import brentq
from analysis.fem_solver.solver import BlockSolver,structured_block,EquilibriumError
from analysis.material.hyperfoam import Hyperfoam


class SolverTests(unittest.TestCase):
    def test_mesh_and_minimal_constraints(self):
        for n in [1,2]:
            s=BlockSolver(Hyperfoam(2000,10,.125),subdivisions=(n,n,n))
            self.assertEqual(len(np.unique(s.X,axis=0)),len(s.X))
            self.assertAlmostEqual(s.assembly.reference_volume,6e-6,places=17)
            self.assertEqual(len(s.anchors),3)
            self.assertEqual(len(s.fixed),2*(n+1)**2+3)
            # An arbitrary transverse affine expansion is admissible under the pins.
            x=s.X*np.array([1.07,1.12,.8]);q=((x-s.X)/s.H).ravel()[s.free]
            np.testing.assert_allclose(s.constrained_positions(q,.002),x,atol=1e-17)
        for bad in [(0,1,1),(1.,1.,1.),(1,2)]:
            with self.assertRaises(ValueError):structured_block(subdivisions=bad)

    def test_zero_load(self):
        s=BlockSolver(Hyperfoam(2000,10,.125),subdivisions=(2,2,2));r=s.solve_force(0)
        np.testing.assert_allclose(r.positions,s.X,atol=1e-15)
        self.assertLess(abs(r.energy),1e-22);self.assertLess(abs(r.top_reaction),1e-10)
        self.assertLess(r.free_residual,1e-8)

    def test_exact_potential_gradient_with_external_work(self):
        s=BlockSolver(Hyperfoam(2000,10,.125));q=np.zeros(len(s.free))
        # Non-equilibrium state, nonzero dead loads: check the exact returned potential.
        loads=np.random.default_rng(2).normal(size=s.X.shape)*.003
        value,g,*_=s.objective(q,.001,loads);h=1e-6;numeric=np.zeros_like(q)
        for j in range(len(q)):
            step=np.zeros_like(q);step[j]=h
            numeric[j]=(s.objective(q+step,.001,loads)[0]-s.objective(q-step,.001,loads)[0])/(2*h)
        self.assertLess(np.linalg.norm(g-numeric)/np.linalg.norm(g),1e-7)

    def test_prescribed_and_force_control(self):
        for alpha,beta in [(10,0),(20,0),(10,.125)]:
            m=Hyperfoam(2000,alpha,beta);s=BlockSolver(m,subdivisions=(2,2,2))
            r=s.solve_displacement(.003)
            F,W,P,*_=m.free_uniaxial(.7);expected=s.X@F.T
            self.assertLess(np.max(abs(r.positions-expected)),2e-8)
            self.assertLess(abs(r.top_reaction+.0006*P[2,2]),2e-7)
            self.assertLess(abs(r.energy-6e-6*W),1e-10)
            target=.15;sol=s.solve_force(target)
            root=brentq(lambda lam:-.0006*m.free_uniaxial(lam)[2][2,2]-target,.35,1)
            self.assertLess(abs(sol.displacement-.01*(1-root)),2e-8)
            self.assertLess(abs(sol.top_reaction-target),2e-7)
            self.assertLess(abs(sol.bottom_reaction-target),5e-7)
            self.assertLess(sol.free_residual,1.01e-8)
            self.assertGreater(sol.min_J,0)

    def test_nonaffine_initial_guess_and_feasible_segment(self):
        rng=np.random.default_rng(6)
        for alpha,beta in [(10,0),(20,0),(10,.125)]:
            s=BlockSolver(Hyperfoam(2000,alpha,beta),subdivisions=(2,2,2));r=s.solve_displacement(.002)
            x=r.positions.copy()
            x.ravel()[s.free]+=rng.normal(size=len(s.free))*2e-5
            perturbed=replace(r,positions=x)
            actual=s.solve_displacement(.002,start=perturbed)
            self.assertGreater(actual.iterations,0)
            self.assertLess(np.max(abs(actual.positions-r.positions)),2e-8)
        q=((actual.positions-s.X)/s.H).ravel()[s.free]
        _,_,state,x,_=s.objective(q,.002)
        direction=rng.normal(size=len(q))*20
        step=s._feasible_step(x,direction,state)
        self.assertLess(step,1.)
        for fraction in np.linspace(0,1,20):
            _,_,st,*_=s.objective(q+fraction*step*direction,.002)
            self.assertGreater(min(e.J for e in st.elements),0)
        self.assertTrue(all(h['min_J']>0 for h in actual.history))

    def test_failure_is_not_success(self):
        s=BlockSolver(Hyperfoam(2000,10,.125),max_iterations=1)
        with self.assertRaises(EquilibriumError):s.solve_displacement(.002,max_increment_fraction=.2)
        self.assertTrue(any(a['status']=='failed_retry_smaller_increment' for a in s.continuation_attempts))
        s=BlockSolver(Hyperfoam(2000,10,0))
        with self.assertRaises(EquilibriumError):s.solve_force(10,max_compression_fraction=.05)
        with self.assertRaises(ValueError):s.solve_displacement(.01)
        with self.assertRaises(ValueError):s.solve_force(-1)


if __name__=='__main__':unittest.main()
