"""Bilateral-scenario adapter of Stage 3 safeguarded inverse-BFGS iteration.

The frozen Stage 3 routine mixes minimization with a compressive-only support
policy. This small loop retains its algorithm/settings, calling its unchanged
objective and feasible-step infrastructure, but returns signed plane reactions.
No constitutive, element or gradient formula is duplicated here.
"""
import numpy as np
import time
from scipy.optimize import BFGS
from analysis.fem_solver.solver import Equilibrium,EquilibriumError


def minimize_potential(problem,loads,start=None):
    x=problem.X.copy() if start is None else start.positions.copy()
    q=((x-problem.X)/problem.H).ravel()[problem.free]
    value,g,state,x,residual=problem.objective(q,0.,loads)
    update=BFGS(exception_strategy='skip_update',init_scale='auto');update.initialize(len(q),'inv_hess')
    history=[]
    for iteration in range(problem.max_iterations+1):
        if time.perf_counter()>getattr(problem,'deadline',float('inf')):
            raise EquilibriumError('Wall-time budget reached; no unconverged state returned')
        norm=float(np.max(abs(residual.ravel()[problem.free])));jac=np.array([e.J for e in state.elements])
        history.append(dict(iteration=iteration,energy_J=state.energy,potential_J=value*problem.scale,
                            free_residual_N=norm,min_J=float(jac.min()),step_length=0.))
        if norm<=problem.force_tolerance:
            return Equilibrium(0.,x.copy(),state.energy,value*problem.scale,0.,float(residual[problem.bottom,2].sum()),
                               norm,float(jac.min()),float(jac.max()),iteration,'converged_free_force_residual',history,residual.copy())
        if iteration==problem.max_iterations:break
        direction=-update.get_matrix()@g
        if not np.isfinite(direction).all() or g@direction>=0:
            update.initialize(len(q),'inv_hess');direction=-g
        step=problem._feasible_step(x,direction,state);slope=float(g@direction);accepted=False
        for _ in range(60):
            try:trial=problem.objective(q+step*direction,0.,loads)
            except ValueError:trial=None
            if trial is not None and trial[0]<=value+1e-4*step*slope:
                accepted=True;break
            step*=.5
        if not accepted or np.max(abs(step*direction))<2e-16:
            raise EquilibriumError(f'Line search stagnated at residual {norm:.3g} N')
        newq=q+step*direction;newvalue,newg,newstate,newx,newresidual=trial
        update.update(newq-q,newg-g);history[-1]['step_length']=step
        q,value,g,state,x,residual=newq,newvalue,newg,newstate,newx,newresidual
    raise EquilibriumError(f'Iteration limit: residual {norm:.3g} N, min J {jac.min():.3g}')
