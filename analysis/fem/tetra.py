"""Four-node total-Lagrangian tetrahedra and minimal verification assembly.

Coordinates: metres, row a = node a's xyz. F and stresses use column vectors.
Energy: joules; energy_gradient: N (dE/dx); internal_forces = -energy_gradient.
P is first Piola stress (Pa), NOT Cauchy stress. Integration uses reference volume.
Negative reference determinant is allowed as a node-order convention; current
orientation must match it (det F > 0). Nothing is reordered, clamped or repaired.
Reference edge condition number > 1e12 is rejected as numerically ill-conditioned.
No equilibrium solver, Hessian, contact, damping or sponge geometry is provided.
"""
from dataclasses import dataclass
import math
import numpy as np
from analysis.material.hyperfoam import Hyperfoam


def _positions(value, count=None):
    raw=np.asarray(value)
    if raw.ndim!=2 or raw.shape[1]!=3 or (count is not None and raw.shape[0]!=count) or np.iscomplexobj(raw):
        raise ValueError('Positions must be a real (N,3) array with the required node count')
    result=np.array(raw,dtype=float,copy=True)
    if not np.isfinite(result).all():raise ValueError('Positions must be finite')
    return result


def _edges(x):
    return (x[1:]-x[0]).T


@dataclass(frozen=True)
class ElementState:
    F: np.ndarray
    J: float
    energy: float
    W: float
    P: np.ndarray
    cauchy: np.ndarray
    energy_gradient: np.ndarray
    internal_forces: np.ndarray


class Tet4:
    def __init__(self, reference_positions):
        X=_positions(reference_positions,4)
        try:
            with np.errstate(over='raise',invalid='raise',divide='raise'):
                Dm=_edges(X)
                sign,logdet=np.linalg.slogdet(Dm)
                if sign==0 or not np.isfinite(logdet):raise ValueError('Degenerate reference element')
                condition=float(np.linalg.cond(Dm))
                if not np.isfinite(condition) or condition>1e12:raise ValueError('Ill-conditioned reference element')
                volume=float(np.exp(logdet)/6)
                inverse=np.linalg.solve(Dm,np.eye(3))
                if volume<=0 or not np.isfinite(volume) or not np.isfinite(inverse).all():raise ValueError('Unrepresentable reference geometry')
        except (FloatingPointError,np.linalg.LinAlgError) as exc:
            raise ValueError('Invalid reference element') from exc
        X.setflags(write=False);inverse.setflags(write=False)
        self._X=X;self._inverse=inverse;self._volume=volume
        self.reference_orientation=int(sign);self.reference_condition_number=condition

    @property
    def reference_positions(self):return self._X.copy()

    @property
    def reference_volume(self):return self._volume

    def deformation_gradient(self,current_positions):
        x=_positions(current_positions,4)
        try:
            with np.errstate(over='raise',invalid='raise'):
                F=_edges(x)@self._inverse
                sign,logj=np.linalg.slogdet(F)
                if sign<=0 or not np.isfinite(logj) or not np.isfinite(F).all():raise ValueError('Inverted or degenerate current element')
                J=float(np.exp(logj))
                if J<=0 or not np.isfinite(J):raise ValueError('Unrepresentable current Jacobian')
        except (FloatingPointError,np.linalg.LinAlgError) as exc:
            raise ValueError('Invalid current element') from exc
        return F

    def evaluate(self,current_positions,material: Hyperfoam):
        F=self.deformation_gradient(current_positions)
        W,P,cauchy=material.evaluate(F)
        try:
            with np.errstate(over='raise',invalid='raise'):
                G=self._volume*(P@self._inverse.T)
                gradient=np.empty((4,3));gradient[1:]=G.T;gradient[0]=-np.sum(G,axis=1)
                energy=float(self._volume*W)
                if not np.isfinite(energy) or not np.isfinite(gradient).all():raise ValueError('Nonfinite element response')
        except FloatingPointError as exc:raise ValueError('Unrepresentable element response') from exc
        return ElementState(F,float(np.linalg.det(F)),energy,W,P,cauchy,gradient,-gradient)


@dataclass(frozen=True)
class AssemblyState:
    energy: float
    energy_gradient: np.ndarray
    internal_forces: np.ndarray
    elements: tuple


class TetAssembly:
    """Minimal homogeneous-material assembly for element/patch verification."""
    def __init__(self,reference_positions,connectivity):
        X=_positions(reference_positions)
        cells=np.asarray(connectivity)
        if cells.ndim!=2 or cells.shape[1]!=4 or len(cells)==0 or cells.dtype.kind not in 'iu':raise ValueError('Connectivity must be a nonempty integer (E,4) array')
        if np.any(cells<0) or np.any(cells>=len(X)):raise ValueError('Connectivity index outside node array')
        if any(len(set(row))!=4 for row in cells):raise ValueError('Repeated node in tetrahedron')
        self._X=X;self._cells=cells.astype(np.int64,copy=True)
        self._elements=tuple(Tet4(X[c]) for c in self._cells)
        self._X.setflags(write=False);self._cells.setflags(write=False)

    @property
    def reference_positions(self):return self._X.copy()

    @property
    def connectivity(self):return self._cells.copy()

    @property
    def reference_volume(self):return math.fsum(e.reference_volume for e in self._elements)

    def evaluate(self,current_positions,material):
        x=_positions(current_positions,len(self._X));gradient=np.zeros_like(x);states=[]
        for cell,element in zip(self._cells,self._elements):
            state=element.evaluate(x[cell],material);states.append(state)
            np.add.at(gradient,cell,state.energy_gradient)
        energy=math.fsum(s.energy for s in states)
        if not np.isfinite(energy) or not np.isfinite(gradient).all():raise ValueError('Nonfinite assembled response')
        return AssemblyState(energy,gradient,-gradient,tuple(states))
