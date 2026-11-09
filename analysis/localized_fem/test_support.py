"""KKT checks for the small unilateral bottom-support extension."""
import unittest
import numpy as np
from analysis.localized_fem.support import UnilateralSolver
from analysis.localized_fem.traction import Rectangle
from analysis.localized_fem.solver import TractionSolver,EquilibriumError


class SupportTests(unittest.TestCase):
    def check_kkt(self,s,r):
        d=s.diagnostics(r)
        self.assertGreaterEqual(d['min_bottom_gap_m'],-s.gap_tolerance_m)
        self.assertGreaterEqual(d['min_contact_reaction_N'],-s.force_tolerance)
        self.assertLess(d['complementarity_max_Nm'],1e-14)
        self.assertLessEqual(r.free_residual,s.force_tolerance)
        self.assertLess(d['force_balance_N'],len(s.X)*s.force_tolerance)
        self.assertLess(d['moment_balance_Nm'],len(s.X)*s.force_tolerance*.1)
        self.assertGreater(r.min_J,0)
        self.assertTrue(all(h['min_J']>0 for h in r.history))

    def test_liftoff_and_energy(self):
        p=Rectangle(.01825,.025,.02,.03)
        s=UnilateralSolver();r=s.solve_patch(p,.3);self.check_kkt(s,r)
        self.assertGreater(s.diagnostics(r)['lifted_bottom_nodes'],0)
        b=TractionSolver();bilateral=b.solve_patch(p,.3)
        self.assertLess(r.potential,bilateral.potential)
        inactive=np.setdiff1d(s.bottom,s.active_bottom)
        np.testing.assert_allclose(r.gradient[inactive,2],0,atol=s.force_tolerance)

    def test_reflection_and_translation(self):
        s=UnilateralSolver();l=s.solve_patch(Rectangle(.01825,.025,.02,.03),.3)
        t=UnilateralSolver(origin=(0,0,.057));r=t.solve_patch(Rectangle(.05475,.025,.02,.03),.3)
        self.check_kkt(t,r)
        ids=np.argmin(np.linalg.norm((s.X*np.array([-1,1,1])+[s.lengths[0],0,0])[:,None]-s.X[None,:],axis=2),axis=1)
        np.testing.assert_allclose((l.positions-s.X)[:,2],(r.positions-t.X)[ids,2],atol=2e-9)

    def test_full_top_and_zero(self):
        s=UnilateralSolver();p=Rectangle(.0365,.025,.073,.05)
        r=s.solve_patch(p,0);self.check_kkt(s,r)
        np.testing.assert_allclose(r.positions,s.X,atol=1e-15)
        r=s.solve_patch(p,.3);self.check_kkt(s,r)
        b=TractionSolver();v=b.solve_patch(p,.3)
        np.testing.assert_allclose(r.positions,v.positions,atol=2e-9)

    def test_contact_reactivation(self):
        s=UnilateralSolver();p=Rectangle(.01825,.025,.02,.03)
        # Start an intentionally wrong contact set. The equilibrium must add
        # the bottom nodes whose unconstrained subproblem penetrates the plane.
        s.set_active(np.setdiff1d(s.bottom,[s.bottom[len(s.bottom)//2]]));from analysis.localized_fem.traction import integrate_rectangle
        loads=integrate_rectangle(s.X,s.top_faces,p,.1).nodal_forces_N
        r=s._equilibrate(0,nodal_loads=loads)
        self.assertTrue(any(row['penetrating_nodes'] for row in s.support_log))
        self.assertGreaterEqual((r.positions[s.bottom,2]-s.origin[2]).min(),-s.gap_tolerance_m)

    def test_failure_explicit(self):
        s=UnilateralSolver(max_iterations=1)
        with self.assertRaises(EquilibriumError):s.solve_patch(Rectangle(.01825,.025,.02,.03),.3,load_step=1,min_load_step=1)


if __name__=='__main__':unittest.main(verbosity=2)
