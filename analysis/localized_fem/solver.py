"""Separate free-top prescribed-traction scenario; frozen core is never edited."""
from dataclasses import dataclass
import time
import numpy as np
from analysis.fem_solver.solver import BlockSolver,EquilibriumError,structured_block
from analysis.fem.tetra import TetAssembly
from analysis.material.hyperfoam import Hyperfoam
from analysis.sponge.geometry import outward_boundary
from demo.model import configuration
from analysis.localized_fem.traction import integrate_rectangle
from analysis.localized_fem.minimize import minimize_potential


def symmetric_cells(dimensions,subdivisions):
    """Reflect the verified generator's quarter block, making x/y symmetry exact.

    A one-direction Freudenthal tessellation need not have mirror symmetry.
    Matching reflected quarter faces share integer-grid node IDs, no cracks.
    """
    counts=np.asarray(subdivisions)
    if counts.dtype.kind not in 'iu' or counts.shape!=(3,) or np.any(counts<1) or np.any(counts[:2]%2):
        raise ValueError('Reflection mesh requires positive even x/y cell counts and positive integer z count')
    half=counts.copy();half[:2]//=2;dims=np.asarray(dimensions,float).copy();dims[:2]/=2
    q,c=structured_block(dims,half);indices=np.rint(q/dims*half).astype(int);cells=[]
    shape=tuple(counts+1)
    for sx,sy in [(-1,-1),(-1,1),(1,-1),(1,1)]:
        ijk=indices.copy();ijk[:,0]=counts[0]//2+sx*ijk[:,0];ijk[:,1]=counts[1]//2+sy*ijk[:,1]
        ids=np.ravel_multi_index(ijk.T,shape)
        for cell in c:
            row=ids[cell].copy()
            if sx*sy<0:row[[1,2]]=row[[2,1]]
            cells.append(row)
    return np.array(cells,int)


@dataclass
class LocalizedState:
    positions: np.ndarray
    energy: float
    potential: float
    free_residual: float
    min_J: float
    max_J: float
    gradient: np.ndarray
    iterations: int
    history: list
    attempts: list
    runtime_s: float
    load: object
    termination: str='converged_free_force_residual'


class TractionSolver(BlockSolver):
    """Only bottom z and three existing horizontal anchor DOFs are fixed.

    The inherited exact potential/gradient and positive-J segment bound are
    unchanged. A small inverse-BFGS adapter separates the bilateral reaction
    policy from the frozen routine's tensile-support rejection.
    The parent's displacement argument is always zero: an internal API adapter,
    NOT a top-plane height or a local indentation cap.
    """
    def __init__(self,subdivisions=(2,2,1),origin=(0.,0.,.007),force_tolerance=None,max_iterations=600):
        config=configuration();g=config['geometry_m']
        tolerance=config['inner_force_tolerance_N'] if force_tolerance is None else force_tolerance
        super().__init__(Hyperfoam(config['mu_Pa'],config['alpha'],config['beta']),
                         dimensions=(g['length'],g['width'],g['yellow_height']),subdivisions=subdivisions,
                         origin=origin,force_tolerance=tolerance,max_iterations=max_iterations)
        self.cells=symmetric_cells(self.lengths,subdivisions);self.assembly=TetAssembly(self.X,self.cells)
        self.reference_inverse=np.array([np.linalg.solve((self.X[c[1:]]-self.X[c[0]]).T,np.eye(3)) for c in self.cells])
        self.fixed=np.array(sorted([3*i+2 for i in self.bottom]+[3*i+a for i,a in self.anchors]),int)
        self.free=np.setdiff1d(np.arange(self.X.size),self.fixed)
        self.boundary=outward_boundary(self.X,self.cells)
        self.top_faces=self.boundary[np.all(np.isin(self.boundary,self.top),axis=1)]
        self.subdivisions=tuple(subdivisions)

    def constrained_positions(self,q,displacement):
        if displacement!=0:raise ValueError('No prescribed platen displacement in the traction scenario')
        q=np.asarray(q,float)
        if q.shape!=(len(self.free),) or not np.isfinite(q).all():raise ValueError('Invalid free DOFs')
        x=self.X.copy();x.ravel()[self.free]+=self.H*q;x[self.bottom,2]=self.origin[2]
        return x

    def _equilibrate(self,d,start=None,nodal_loads=None):
        if d!=0:raise ValueError('No global platen displacement')
        loads=np.zeros_like(self.X) if nodal_loads is None else nodal_loads
        return minimize_potential(self,loads,start)

    def solve_displacement(self,*args,**kwargs):raise NotImplementedError('Use solve_patch; there is no global platen')

    def solve_force(self,*args,**kwargs):raise NotImplementedError('Use solve_patch with a declared rectangle')

    def solve_patch(self,rectangle,force,load_step=.25,min_load_step=1/1024):
        if not 0<load_step<=1 or not 0<min_load_step<=load_step:raise ValueError('Invalid continuation factor increment')
        started=time.perf_counter();load=integrate_rectangle(self.X,self.top_faces,rectangle,force)
        state=self._equilibrate(0.,nodal_loads=np.zeros_like(self.X));factor=0.;step=load_step
        histories=[];attempts=[];iterations=0
        solved_states=[dict(force_N=0.,positions=state.positions.copy())]
        while factor<1:
            target=min(1.,factor+step)
            try:next_state=self._equilibrate(0.,start=state,nodal_loads=target*load.nodal_forces_N)
            except EquilibriumError as exc:
                attempts.append(dict(load_factor=target,status='failed_retry',reason=str(exc)))
                step/=2
                if step<min_load_step or 'Wall-time budget' in str(exc):
                    failure=EquilibriumError(f'Continuation failed at factor {target:.6g}: {exc}')
                    failure.attempts=attempts
                    failure.history=histories
                    raise failure from exc
                continue
            attempts.append(dict(load_factor=target,status='converged',reason=''))
            histories.extend(dict(load_factor=target,**r) for r in next_state.history)
            iterations+=next_state.iterations;state=next_state;factor=target
            solved_states.append(dict(force_N=target*force,positions=state.positions.copy()))
        result=LocalizedState(state.positions,state.energy,state.potential,state.free_residual,state.min_J,state.max_J,
                              state.gradient,iterations,histories,attempts,time.perf_counter()-started,load)
        result.solved_states=solved_states
        return result

    def diagnostics(self,state):
        displacement=self.X[:,2]-state.positions[:,2];weights=state.load.shape_integrals_m2
        remainder=state.load.whole_top_integrals_m2-weights;unloaded_area=float(remainder.sum())
        reactions=np.zeros_like(self.X);reactions.ravel()[self.fixed]=state.gradient.ravel()[self.fixed]
        resultant=(reactions+state.load.nodal_forces_N).sum(axis=0)
        moment=np.cross(state.positions,reactions+state.load.nodal_forces_N).sum(axis=0)
        return dict(nodes=len(self.X),tetrahedra=len(self.cells),free_dofs=len(self.free),iterations=state.iterations,runtime_s=state.runtime_s,
                    force_N=state.load.force_N,clipped_area_m2=state.load.area_m2,pressure_Pa=state.load.pressure_Pa,
                    max_downward_mm=float(displacement.max()*1000),loaded_mean_downward_mm=float(weights@displacement/state.load.area_m2*1000),
                    unloaded_mean_downward_mm=float(remainder@displacement/unloaded_area*1000) if unloaded_area>1e-15 else float('nan'),
                    energy_J=state.energy,potential_J=state.potential,support_reaction_N=float(reactions[:,2].sum()),
                    free_residual_N=state.free_residual,force_balance_N=float(np.max(np.abs(resultant))),moment_balance_Nm=float(np.max(np.abs(moment))),
                    min_J=state.min_J,max_J=state.max_J,min_bottom_nodal_reaction_N=float(state.gradient[self.bottom,2].min()),termination=state.termination)
