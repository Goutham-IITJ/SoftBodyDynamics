"""Independent identities and equilibria for the localized scenario."""
import unittest
import numpy as np
from analysis.localized_fem.solver import TractionSolver,EquilibriumError
from analysis.localized_fem.traction import Rectangle,integrate_rectangle

PATCH=Rectangle(.0365,.025,.020,.030)


class LocalizedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.problem=TractionSolver()
        cls.center=cls.problem.solve_patch(PATCH,.3)

    def test_zero(self):
        r=self.problem.solve_patch(PATCH,0)
        np.testing.assert_allclose(r.positions,self.problem.X,atol=1e-15)
        self.assertLess(abs(r.energy),1e-16)

    def test_exact_integration_all_meshes(self):
        for mesh in [(2,2,1),(4,4,2),(6,6,3)]:
            s=TractionSolver(mesh)
            for patch in [PATCH,Rectangle(.002,.045,.02,.03),Rectangle(.01825,.025,.02,.03),Rectangle(.05475,.025,.02,.03)]:
                load=integrate_rectangle(s.X,s.top_faces,patch,.7)
                lo,hi=load.clipped_bounds_xy_m;centroid=(lo+hi)/2
                self.assertAlmostEqual(load.area_m2,np.prod(hi-lo),places=15)
                np.testing.assert_allclose(load.nodal_forces_N.sum(axis=0),[0,0,-.7],atol=1e-14)
                np.testing.assert_allclose(load.centroid_xy_m,centroid,atol=1e-15)
                np.testing.assert_allclose(np.cross(s.X,load.nodal_forces_N).sum(axis=0),[-.7*centroid[1],.7*centroid[0],0],atol=1e-15)
                self.assertGreaterEqual(load.shape_integrals_m2.min(),-1e-17)

    def test_free_top_and_mesh_volume(self):
        s=self.problem
        self.assertTrue(np.isin((3*s.top[:,None]+np.arange(3)).ravel(),s.free).all())
        volume=sum(np.linalg.det((s.X[c[1:]]-s.X[c[0]]).T)/6 for c in s.cells)
        self.assertAlmostEqual(volume,np.prod(s.lengths),places=15)
        self.assertTrue(all(np.linalg.det((s.X[c[1:]]-s.X[c[0]]).T)>0 for c in s.cells))

    def test_nonaffine_total_potential_gradient(self):
        s=self.problem;rng=np.random.default_rng(728)
        q=rng.normal(0,.001,len(s.free));f=integrate_rectangle(s.X,s.top_faces,PATCH,.3).nodal_forces_N
        value,g,*_=s.objective(q,0,f);h=1e-6;numeric=[]
        for i in range(len(q)):
            e=np.zeros_like(q);e[i]=h
            numeric.append((s.objective(q+e,0,f)[0]-s.objective(q-e,0,f)[0])/(2*h))
        np.testing.assert_allclose(numeric,g,atol=2e-10,rtol=2e-6)
        x=s.constrained_positions(q,0);U=s.assembly.evaluate(x,s.material).energy
        self.assertAlmostEqual(value*s.scale,U-np.sum(f*(x-s.X)),places=15)

    def test_balance_and_feasibility(self):
        s=self.problem;r=self.center;d=s.diagnostics(r)
        self.assertLessEqual(r.free_residual,s.force_tolerance)
        self.assertLess(d['force_balance_N'],len(s.X)*s.force_tolerance)
        self.assertLess(d['moment_balance_Nm'],len(s.X)*s.force_tolerance*.1)
        self.assertTrue(all(h['min_J']>0 for h in r.history))
        x=s.X.copy();x[:,2]=2*s.origin[2]-x[:,2]
        with self.assertRaises(ValueError):s.assembly.evaluate(x,s.material)
        q=np.zeros(len(s.free));_,_,state,x,_=s.objective(q,0,None)
        direction=np.random.default_rng(4).normal(size=len(q))*10
        step=s._feasible_step(x,direction,state)
        for fraction in np.linspace(0,1,11):
            st=s.assembly.evaluate(s.constrained_positions(q+fraction*step*direction,0),s.material)
            self.assertTrue(all(e.J>0 for e in st.elements))

    def test_symmetry_and_translation(self):
        s=self.problem;u=self.center.positions-s.X
        for axis in [0,1]:
            reflected=s.X.copy();reflected[:,axis]=s.lengths[axis]-reflected[:,axis]
            ids=np.argmin(np.linalg.norm(reflected[:,None]-s.X[None,:],axis=2),axis=1)
            np.testing.assert_allclose(u[:,2],u[ids,2],atol=2e-9)
            centered=u-u.mean(axis=0);target=centered[ids].copy();target[:,axis]*=-1
            np.testing.assert_allclose(centered,target,atol=2e-9)
        shifted=TractionSolver(origin=(0,0,.057));r=shifted.solve_patch(PATCH,.3)
        np.testing.assert_allclose(r.positions-shifted.X,u,atol=2e-9)
        self.assertAlmostEqual(r.energy,self.center.energy,places=11)

    def test_placement(self):
        s=self.problem
        left=s.solve_patch(Rectangle(.01825,.025,.02,.03),.3)
        right=s.solve_patch(Rectangle(.05475,.025,.02,.03),.3)
        ids=np.argmin(np.linalg.norm((s.X*np.array([-1,1,1])+[s.lengths[0],0,0])[:,None]-s.X[None,:],axis=2),axis=1)
        np.testing.assert_allclose((left.positions-s.X)[:,2],(right.positions-s.X)[ids,2],atol=2e-9)
        self.assertFalse(np.allclose(left.load.nodal_forces_N,right.load.nodal_forces_N))

    def test_bad_inputs_and_failure(self):
        for patch in [Rectangle(1,1,.01,.01)]:
            with self.assertRaises(ValueError):integrate_rectangle(self.problem.X,self.problem.top_faces,patch,.3)
        with self.assertRaises(ValueError):Rectangle(0,0,0,.1)
        with self.assertRaises(ValueError):TractionSolver((3,2,1))
        with self.assertRaises(ValueError):self.problem.solve_patch(PATCH,-1)
        with self.assertRaises(EquilibriumError):TractionSolver(max_iterations=1).solve_patch(PATCH,.3,load_step=1,min_load_step=1)

    def test_uniform_full_top_analytical_solution(self):
        from scipy.optimize import brentq
        s=self.problem;force=.3;area=np.prod(s.lengths[:2])
        stretch=brentq(lambda lam:-area*s.material.free_uniaxial(lam)[2][2,2]-force,.8,1)
        r=s.solve_patch(Rectangle(.0365,.025,.073,.050),force)
        expected=s.X.copy();expected[:,2]=s.origin[2]+stretch*(s.X[:,2]-s.origin[2])
        np.testing.assert_allclose(r.positions,expected,atol=2e-9)
        energy=s.material.free_uniaxial(stretch)[1]*s.assembly.reference_volume
        # Fixed force residual permits ~1e-6 relative strain/energy error at this load.
        np.testing.assert_allclose(r.energy,energy,rtol=2e-6,atol=1e-12)


if __name__=='__main__':unittest.main(verbosity=2)
