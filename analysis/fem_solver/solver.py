"""Homogeneous quasi-static block solver with configurable reference origin (SI).

Reuses Stage 2 elements. Full-face, frictionless *bilateral* support/platen BCs
are imposed by DOF elimination, not general contact. No layered material or fit.
"""
from dataclasses import dataclass
import itertools
import numpy as np
from scipy.optimize import BFGS, brentq
from analysis.fem.tetra import TetAssembly


def structured_block(dimensions=(.03,.02,.01), subdivisions=(1,1,1)):
    lengths=np.asarray(dimensions,float)
    counts=np.asarray(subdivisions)
    if lengths.shape!=(3,) or not np.isfinite(lengths).all() or np.any(lengths<=0):raise ValueError('Require three positive finite dimensions in metres')
    if counts.shape!=(3,) or counts.dtype.kind not in 'iu' or np.any(counts<1):raise ValueError('Require three positive integer subdivisions')
    ids={p:i for i,p in enumerate(itertools.product(*(range(int(n)+1) for n in counts)))}
    X=np.array(list(ids),float)/counts*lengths;cells=[]
    for base in itertools.product(*(range(int(n)) for n in counts)):
        for order in itertools.permutations(range(3)):
            p=np.array(base);tet=[ids[tuple(p)]]
            for a in order:
                p=p.copy();p[a]+=1;tet.append(ids[tuple(p)])
            # Define positive reference orientation explicitly at construction.
            vertices=X[tet];D=(vertices[1:]-vertices[0]).T
            if np.linalg.det(D)<0:tet[1],tet[2]=tet[2],tet[1]
            cells.append(tet)
    cells=np.asarray(cells,int)
    if len(np.unique(X,axis=0))!=len(X):raise ValueError('Duplicate reference nodes')
    volume=0.
    for tet in cells:
        determinant=np.linalg.det((X[tet[1:]]-X[tet[0]]).T)
        if determinant<=0:raise ValueError('Nonpositive reference cell')
        volume+=determinant/6
    if not np.isclose(volume,np.prod(lengths),rtol=1e-12,atol=0):raise ValueError('Incorrect mesh volume')
    return X,cells


class EquilibriumError(RuntimeError):pass


@dataclass
class Equilibrium:
    displacement: float
    positions: np.ndarray
    energy: float
    potential: float
    top_reaction: float
    bottom_reaction: float
    free_residual: float
    min_J: float
    max_J: float
    iterations: int
    termination: str
    history: list
    gradient: np.ndarray


class BlockSolver:
    def __init__(self,material,dimensions=(.03,.02,.01),subdivisions=(1,1,1),force_tolerance=1e-8,max_iterations=600,origin=(0.,0.,0.)):
        self.material=material
        self.X,self.cells=structured_block(dimensions,subdivisions)
        self.lengths=np.asarray(dimensions,float);self.H=self.lengths[2]
        raw_origin=np.asarray(origin)
        if raw_origin.shape!=(3,) or np.iscomplexobj(raw_origin):raise ValueError('Origin must be a finite real 3-vector')
        self.origin=np.asarray(raw_origin,float).copy()
        if not np.isfinite(self.origin).all():raise ValueError('Origin must be finite')
        # Identify the local surfaces/anchors before translating the geometry.
        self.top=np.flatnonzero(self.X[:,2]==self.H);self.bottom=np.flatnonzero(self.X[:,2]==0)
        origin_node=np.argmin(np.linalg.norm(self.X,axis=1))
        xcorner=np.argmin(np.linalg.norm(self.X-[self.lengths[0],0,0],axis=1))
        self.X+=self.origin
        self.assembly=TetAssembly(self.X,self.cells)
        self.scale=material.mu*self.assembly.reference_volume
        self.force_tolerance=float(force_tolerance);self.max_iterations=int(max_iterations)
        if not np.isfinite(self.force_tolerance) or self.force_tolerance<=0 or self.max_iterations<1:raise ValueError('Invalid solver tolerances')
        # bottom z, top z, origin x/y, second bottom corner y (yaw).
        self.anchors=[(int(origin_node),0),(int(origin_node),1),(int(xcorner),1)]
        self.fixed=np.array(sorted(set([3*i+2 for i in self.bottom]+[3*i+2 for i in self.top]+[3*i+a for i,a in self.anchors])),int)
        self.free=np.setdiff1d(np.arange(self.X.size),self.fixed)
        self.reference_inverse=np.array([np.linalg.solve((self.X[c[1:]]-self.X[c[0]]).T,np.eye(3)) for c in self.cells])
        self.cache={};self.force_history=[];self.continuation_attempts=[];self.last_equilibrium=None

    def constrained_positions(self,q,displacement):
        q=np.asarray(q,float)
        if q.shape!=(len(self.free),) or not np.isfinite(q).all():raise ValueError('Invalid free DOFs')
        x=self.X.copy();x.ravel()[self.free]+=self.H*q
        x[self.top,2]=self.origin[2]+self.H-displacement;x[self.bottom,2]=self.origin[2]
        return x

    def objective(self,q,displacement,nodal_loads=None):
        """Exact reduced potential and its analytic dimensionless gradient.
        Nodal loads are dead loads in N; work = f dot (x-X), in joules.
        """
        if not np.isfinite(displacement) or displacement<0 or displacement>=self.H:raise ValueError('Invalid compression displacement')
        x=self.constrained_positions(q,displacement)
        loads=np.zeros_like(x) if nodal_loads is None else np.asarray(nodal_loads,float)
        if loads.shape!=x.shape or not np.isfinite(loads).all():raise ValueError('Invalid nodal dead loads')
        state=self.assembly.evaluate(x,self.material)
        potential=state.energy-float(np.sum(loads*(x-self.X)))
        residual=state.energy_gradient-loads
        return potential/self.scale,self.H*residual.ravel()[self.free]/self.scale,state,x,residual

    def _feasible_step(self,x,direction,state):
        """Bound ||alpha F^-1 deltaF||_2 <= 0.5, staying in det F > 0
        on the entire trial segment, not just at its endpoint (Neumann bound).
        This limits step length without altering energy or constitutive stiffness.
        """
        delta=np.zeros_like(x);delta.ravel()[self.free]=self.H*direction
        edges=np.transpose(delta[self.cells[:,1:]]-delta[self.cells[:,0,None]],(0,2,1))
        dF=edges@self.reference_inverse
        worst=max(np.linalg.norm(np.linalg.solve(s.F,df),ord=2) for s,df in zip(state.elements,dF))
        return min(1.,.5/worst) if worst>0 else 1.

    def _equilibrate(self,d,start=None,nodal_loads=None):
        if start is None:x=self.X.copy()
        else:
            x=start.positions.copy()
            # Geometric continuation predictor; no material-point analytic solution.
            x[:,2]=self.origin[2]+(x[:,2]-self.origin[2])*(self.H-d)/(self.H-start.displacement)
        q=((x-self.X)/self.H).ravel()[self.free]
        value,g,state,x,residual=self.objective(q,d,nodal_loads)
        update=BFGS(exception_strategy='skip_update',init_scale='auto');update.initialize(len(q),'inv_hess')
        history=[]
        for iteration in range(self.max_iterations+1):
            norm=float(np.max(np.abs(residual.ravel()[self.free])))
            jac=np.array([s.J for s in state.elements])
            history.append(dict(iteration=iteration,energy_J=state.energy,potential_J=value*self.scale,free_residual_N=norm,min_J=float(jac.min()),step_length=0.))
            if norm<=self.force_tolerance:
                top=-float(residual[self.top,2].sum());bottom=float(residual[self.bottom,2].sum())
                if np.min(residual[self.bottom,2])<-10*self.force_tolerance:raise EquilibriumError('Full-support assumption requires tensile table reaction')
                return Equilibrium(d,x.copy(),state.energy,value*self.scale,top,bottom,norm,float(jac.min()),float(jac.max()),iteration,'converged_free_force_residual',history,residual.copy())
            if iteration==self.max_iterations:break
            direction=-update.get_matrix()@g
            if not np.isfinite(direction).all() or np.dot(g,direction)>=0:
                update.initialize(len(q),'inv_hess');direction=-g
            step=self._feasible_step(x,direction,state);slope=float(g@direction)
            accepted=False
            for _ in range(60):
                try:trial=self.objective(q+step*direction,d,nodal_loads)
                except ValueError:trial=None
                if trial is not None and trial[0]<=value+1e-4*step*slope:
                    accepted=True;break
                step*=.5
            if not accepted or np.max(np.abs(step*direction))<2e-16:
                raise EquilibriumError(f'Line search stagnated at residual {norm:.3g} N')
            newq=q+step*direction;newvalue,newg,newstate,newx,newresidual=trial
            update.update(newq-q,newg-g);history[-1]['step_length']=step
            q,value,g,state,x,residual=newq,newvalue,newg,newstate,newx,newresidual
        raise EquilibriumError(f'Iteration limit: residual {norm:.3g} N, min J {jac.min():.3g}')

    def solve_displacement(self,displacement,start=None,max_increment_fraction=.05,nodal_loads=None):
        d=float(displacement)
        if not np.isfinite(d) or d<0 or d>=self.H:raise ValueError('Require 0<=d<H')
        if not np.isfinite(max_increment_fraction) or max_increment_fraction<=0:raise ValueError('Invalid continuation increment')
        if start is None:start=self._equilibrate(0.,nodal_loads=nodal_loads)
        if d==start.displacement:
            result=self._equilibrate(d,start,nodal_loads);self.last_equilibrium=result
            return result
        current=start;increment=np.sign(d-current.displacement)*min(abs(d-current.displacement),max_increment_fraction*self.H)
        all_history=[];total_iterations=0
        while abs(d-current.displacement)>1e-14*self.H:
            target=current.displacement+np.sign(increment)*min(abs(increment),abs(d-current.displacement))
            try:next_state=self._equilibrate(target,current,nodal_loads)
            except EquilibriumError as exc:
                self.continuation_attempts.append(dict(displacement_m=target,status='failed_retry_smaller_increment',reason=str(exc)))
                increment*=.5
                if abs(increment)<1e-6*self.H:raise
                continue
            self.continuation_attempts.append(dict(displacement_m=target,status=next_state.termination,reason=''))
            for row in next_state.history:all_history.append(dict(platen_displacement_m=target,**row))
            total_iterations+=next_state.iterations;current=next_state
        current.history=all_history;current.iterations=total_iterations
        self.last_equilibrium=current
        return current

    def solve_force(self,force,max_compression_fraction=.65,root_tolerance_m=1e-10):
        target=float(force)
        if not np.isfinite(target) or target<0:raise ValueError('Require finite nonnegative compressive force')
        if not 0<max_compression_fraction<1:raise ValueError('Invalid force-control search domain')
        if not np.isfinite(root_tolerance_m) or root_tolerance_m<=0:raise ValueError('Invalid root tolerance')
        warm=self.last_equilibrium
        if 0. not in self.cache:self.cache[0.]=self.solve_displacement(0.)
        if target==0:
            # Re-equilibrate from the actual loaded state; do not return a cached shape.
            result=self.solve_displacement(0.,start=warm if warm is not None else self.cache[0.])
            if abs(result.top_reaction)>2e-7:raise EquilibriumError('Zero-force unloading reaction failed')
            self.cache[0.]=result
            return result
        def reaction(d):
            if d not in self.cache:
                near=min(self.cache,key=lambda z:abs(z-d))
                self.cache[d]=self.solve_displacement(d,start=self.cache[near])
            s=self.cache[d]
            self.force_history.append(dict(target_N=target,displacement_m=d,reaction_N=s.top_reaction,residual_N=s.top_reaction-target,free_residual_N=s.free_residual,min_J=s.min_J,termination=s.termination))
            return s.top_reaction-target
        lo=0.;hi=.05*self.H;cap=max_compression_fraction*self.H
        while reaction(hi)<0:
            if hi>=cap:raise EquilibriumError('Target force not bracketed in declared compression domain')
            lo=hi;hi=min(1.6*hi,cap)
        root=brentq(reaction,lo,hi,xtol=root_tolerance_m,rtol=1e-12)
        reaction(root);result=self.cache[root]
        if abs(result.top_reaction-target)>max(2e-7,2e-6*target):raise EquilibriumError('Outer reaction balance failed')
        # Total force-driven potential includes constant platen load work -target*d.
        result.potential=result.energy-target*result.displacement
        self.last_equilibrium=result
        return result
