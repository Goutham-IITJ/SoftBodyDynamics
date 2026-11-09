"""Frozen Stage 5 model, using the verified FEM without fitting or surrogates."""
from pathlib import Path
import csv
import hashlib
import json
import numpy as np
from analysis.material.hyperfoam import Hyperfoam
from analysis.sponge.geometry import Sponge,SpongeConfig

ROOT=Path(__file__).resolve().parents[1]
PARAMETERS=ROOT/'analysis/calibration/outputs/parameters.csv'
CORE=['analysis/material/hyperfoam.py','analysis/fem/tetra.py',
      'analysis/fem_solver/solver.py','analysis/sponge/geometry.py']
CONDITION='centered_full_face_stationary'


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def configuration(scenario='primary'):
    if scenario not in ['primary','alpha20']:raise ValueError('Only frozen primary and labeled alpha20 comparison are supported')
    with PARAMETERS.open(newline='',encoding='utf-8') as f:
        row=next(r for r in csv.DictReader(f) if r['scenario']==scenario)
    alpha,beta,mu=(float(row[k]) for k in ['alpha','beta','mu_Pa'])
    if alpha!=(10 if scenario=='primary' else 20) or beta!=0 or not np.isfinite(mu) or mu<=0:
        raise ValueError('Official Stage 5 assumptions changed; review rather than silently update')
    from dataclasses import asdict
    result=dict(scenario=scenario,mu_Pa=mu,alpha=alpha,beta=beta,
                geometry_m=asdict(SpongeConfig()),subdivisions=[2,2,2],
                inner_force_tolerance_N=5e-8,maximum_compression_fraction=.65,
                gravity_m_s2=9.81,nominal_demonstration_tare_g=75,
                parameters_sha256=hashlib.sha256(PARAMETERS.read_bytes()).hexdigest(),
                core_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in CORE})
    frozen=Path(__file__).resolve().parent/'frozen_models.json'
    if not frozen.exists():raise ValueError('Missing reviewed frozen model snapshot')
    if json.loads(frozen.read_text())[scenario]!=result:
        raise ValueError('Stage 5 parameters, geometry or verified core changed from the frozen demonstration; review required')
    return result


def new_sponge(config):
    s=Sponge(config=SpongeConfig(**config['geometry_m']),subdivisions=tuple(config['subdivisions']),
             material=Hyperfoam(config['mu_Pa'],config['alpha'],config['beta']))
    s.solver.force_tolerance=config['inner_force_tolerance_N']
    return s


def solve(sponge,force):
    state=sponge.solver.solve_force(force,max_compression_fraction=.65)
    if state.termination!='converged_free_force_residual' or state.min_J<=0 or state.free_residual>5.001e-8:
        raise RuntimeError('Invalid equilibrium')
    if not 0<=state.displacement<=sponge.config.yellow_height*.65:raise RuntimeError('Compression outside declared domain')
    if abs(state.top_reaction-force)>max(2e-7,2e-6*force):raise RuntimeError('Applied force mismatch')
    if abs(state.top_reaction-state.bottom_reaction)>2e-6:raise RuntimeError('Top/bottom force imbalance')
    if any(h['min_J']<=0 for h in state.history):raise RuntimeError('Nonpositive history Jacobian')
    return state
