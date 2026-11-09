"""One-scale inverse FEM problem. No empirical surrogate or material equations.

SI units throughout. For fixed alpha/beta and displacement, U and dU/dx scale
linearly with mu. Thus x(F;mu) = x(F*MU_REFERENCE/mu;MU_REFERENCE).
Every objective prediction still calls the Stage 3 force-controlled FEM solver.
"""
from dataclasses import dataclass,replace
from pathlib import Path
import csv
import numpy as np
from scipy.optimize import minimize_scalar
from analysis.material.hyperfoam import Hyperfoam
from analysis.sponge.geometry import Sponge

G=9.81
MU_REFERENCE=2000.
MAX_COMPRESSION_FRACTION=.65  # unchanged Stage 3 search limit: 13 mm yellow
CALIBRATION_FORCE_TOLERANCE=5e-8  # N; avoid near-reference line-search roundoff
SOURCE=Path(__file__).resolve().parents[1]/'outputs'/'cycle_summary.csv'


def force_from_water(water_ml,tare_g=75.):
    """Assume water density 1 g/ml; tare is an assumed shared bottle mass."""
    water=np.asarray(water_ml,float)
    if not np.isfinite(water).all() or np.any(water<0) or not np.isfinite(tare_g) or tare_g<0:
        raise ValueError('Masses must be finite and nonnegative')
    return (water+tare_g)*G/1000


def training_observations(path=SOURCE,cycles=(1,1)):
    """Explicit endpoint-only interface; intermediate rows cannot enter fitting."""
    with Path(path).open(newline='',encoding='utf-8') as f:rows=list(csv.DictReader(f))
    selected=[]
    for video,cycle in zip(['500ml','1000ml'],cycles):
        matches=[r for r in rows if r['video']==video and int(r['cycle'])==cycle]
        if len(matches)!=1:raise ValueError('Expected one source row per endpoint')
        selected.append(float(matches[0]['hold_compression_mm'])/1000)
    return np.asarray(selected)


@dataclass(frozen=True)
class Fit:
    mu: float
    alpha: float
    beta: float
    predicted_m: tuple
    residual_m: tuple
    rmse_m: float
    evaluations: int
    lower_mu: float
    upper_mu: float
    success: bool


class FEMResponse:
    def __init__(self,alpha=10.,beta=0.,subdivisions=(1,1,1)):
        self.alpha=float(alpha);self.beta=float(beta)
        self.sponge=Sponge(subdivisions=subdivisions,material=Hyperfoam(MU_REFERENCE,alpha,beta))
        self.sponge.solver.force_tolerance=CALIBRATION_FORCE_TOLERANCE
        self.trace=[]
        self.cap=self.sponge.config.yellow_height*MAX_COMPRESSION_FRACTION
        self.cap_state=self.sponge.solve_displacement(self.cap)
        self.capacity_reference=self.cap_state.top_reaction

    def predict(self,force,mu):
        if not np.isfinite(mu) or mu<=0:raise ValueError('Require positive finite mu')
        target=float(force)
        if not np.isfinite(target) or target<0:raise ValueError('Require nonnegative finite force')
        if target>self.capacity_reference*mu/MU_REFERENCE:
            raise ValueError('Force exceeds unchanged 65% compression domain')
        state=self.sponge.solver.solve_force(target*MU_REFERENCE/mu,max_compression_fraction=MAX_COMPRESSION_FRACTION)
        scale=mu/MU_REFERENCE
        # Preserve solver-owned cached states; scale only dimensional mechanical fields.
        history=[dict(h,energy_J=h['energy_J']*scale,potential_J=h['potential_J']*scale,free_residual_N=h['free_residual_N']*scale) for h in state.history]
        return replace(state,energy=state.energy*scale,potential=state.energy*scale-target*state.displacement,top_reaction=state.top_reaction*scale,bottom_reaction=state.bottom_reaction*scale,free_residual=state.free_residual*scale,gradient=state.gradient*scale,history=history)

    def fit(self,forces,observed_m):
        forces=np.asarray(forces,float);observed=np.asarray(observed_m,float)
        if forces.shape!=(2,) or observed.shape!=(2,) or not np.isfinite(forces).all() or not np.isfinite(observed).all():
            raise ValueError('Require exactly two finite endpoint observations')
        if np.any(forces<=0) or forces[1]<=forces[0] or np.any(observed<=0) or np.any(observed>=self.cap):
            raise ValueError('Invalid force order or observed compression domain')
        lower=max(1.,float(forces.max())*MU_REFERENCE/self.capacity_reference*(1+1e-5));upper=1e6
        if lower>=upper:raise ValueError('No admissible scale interval')
        count=0
        def objective(logmu):
            nonlocal count
            mu=float(np.exp(logmu));pred=np.array([self.predict(f,mu).displacement for f in forces])
            loss=float(np.sum((pred-observed)**2));count+=1
            self.trace.append(dict(evaluation=len(self.trace),alpha=self.alpha,beta=self.beta,mu_Pa=mu,observed_low_m=observed[0],observed_high_m=observed[1],force_low_N=forces[0],force_high_N=forces[1],predicted_low_m=pred[0],predicted_high_m=pred[1],sum_squared_displacement_m2=loss))
            return loss
        result=minimize_scalar(objective,bounds=(np.log(lower),np.log(upper)),method='bounded',options=dict(xatol=1e-7,maxiter=100))
        if not result.success:raise RuntimeError(f'Calibration failed: {result.message}')
        mu=float(np.exp(result.x))
        if min(result.x-np.log(lower),np.log(upper)-result.x)<1e-4:raise RuntimeError('Scale optimum at declared admissible bound')
        pred=np.array([self.predict(f,mu).displacement for f in forces]);res=pred-observed
        return Fit(mu,self.alpha,self.beta,tuple(pred),tuple(res),float(np.sqrt(np.mean(res**2))),count,lower,upper,True)
