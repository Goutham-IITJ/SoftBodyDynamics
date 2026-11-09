"""Minimal nodal, frictionless unilateral bottom plane; no indenter contact."""
import numpy as np
from analysis.localized_fem.solver import TractionSolver,EquilibriumError
from analysis.localized_fem.minimize import minimize_potential


class UnilateralSolver(TractionSolver):
    """Active-set subproblems reuse the safeguarded unconstrained minimizer.

    Intermediate subproblem solutions may violate contact; they are NOT accepted
    load states. Only a positive-J KKT solution is returned. Failure/cycling is
    explicit, without penalties, reaction clipping or changes to material energy.
    """
    gap_tolerance_m=1e-10
    max_active_iterations=20

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.active_bottom=self.bottom.copy()
        self.support_log=[]

    def set_active(self,nodes):
        self.active_bottom=np.asarray(sorted(set(nodes)),int)
        self.fixed=np.array(sorted([3*i+2 for i in self.active_bottom]+[3*i+a for i,a in self.anchors]),int)
        self.free=np.setdiff1d(np.arange(self.X.size),self.fixed)

    def constrained_positions(self,q,displacement):
        if displacement!=0:raise ValueError('No top platen')
        q=np.asarray(q,float)
        if q.shape!=(len(self.free),) or not np.isfinite(q).all():raise ValueError('Invalid free DOFs')
        x=self.X.copy();x.ravel()[self.free]+=self.H*q
        x[self.active_bottom,2]=self.origin[2]
        return x

    def _equilibrate(self,d,start=None,nodal_loads=None):
        if d!=0:raise ValueError('No top platen')
        loads=np.zeros_like(self.X) if nodal_loads is None else nodal_loads
        all_history=[];iterations=0;seen=set()
        for outer in range(self.max_active_iterations):
            key=tuple(self.active_bottom)
            if key in seen:raise EquilibriumError('Bottom active set cycled; no admissible solution returned')
            seen.add(key)
            state=minimize_potential(self,loads,start)
            iterations+=state.iterations
            all_history.extend(dict(active_set_iteration=outer,**h) for h in state.history)
            gap=state.positions[self.bottom,2]-self.origin[2]
            inactive=np.setdiff1d(self.bottom,self.active_bottom)
            penetrating=inactive[state.positions[inactive,2]-self.origin[2]<-self.gap_tolerance_m]
            tensile=self.active_bottom[state.gradient[self.active_bottom,2]<-self.force_tolerance]
            self.support_log.append(dict(force_N=float(-loads[:,2].sum()),outer=outer,active_nodes=len(self.active_bottom),min_gap_m=float(gap.min()),min_active_reaction_N=float(state.gradient[self.active_bottom,2].min()) if len(self.active_bottom) else 0.,penetrating_nodes=len(penetrating),tensile_nodes=len(tensile)))
            if len(penetrating):
                self.set_active(np.union1d(self.active_bottom,penetrating))
            elif len(tensile):
                self.set_active(np.setdiff1d(self.active_bottom,tensile))
            else:
                state.iterations=iterations;state.history=all_history
                return state
            start=state
        raise EquilibriumError('Bottom active-set iteration limit; no admissible solution returned')

    def solve_patch(self,*args,**kwargs):
        self.set_active(self.bottom);self.support_log=[]
        state=super().solve_patch(*args,**kwargs)
        state.active_bottom=self.active_bottom.copy()
        state.support_log=self.support_log.copy()
        state.termination='converged_unilateral_KKT'
        return state

    def diagnostics(self,state):
        self.set_active(state.active_bottom)
        result=super().diagnostics(state)
        gap=state.positions[self.bottom,2]-self.origin[2]
        reaction=np.zeros(len(self.bottom))
        mask=np.isin(self.bottom,self.active_bottom)
        reaction[mask]=state.gradient[self.bottom[mask],2]
        result.update(support='unilateral frictionless nodal plane',active_bottom_nodes=int(mask.sum()),lifted_bottom_nodes=int((gap>self.gap_tolerance_m).sum()),min_bottom_gap_m=float(gap.min()),max_bottom_gap_mm=float(gap.max()*1000),min_contact_reaction_N=float(reaction.min()),complementarity_max_Nm=float(np.max(abs(gap*reaction))),gap_tolerance_m=self.gap_tolerance_m)
        return result
