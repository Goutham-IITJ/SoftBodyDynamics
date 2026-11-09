"""Reproducible Stage 5 fits, frozen evaluation, sensitivity, and numeric audit.

Run: python -B analysis/calibration/run_calibration.py
All writes are restricted to this stage directory; prior files are hash protected.
"""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import csv
import hashlib
import itertools
import json
from dataclasses import asdict
import numpy as np
import scipy
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from analysis.calibration.calibrate import (FEMResponse,training_observations,force_from_water,
                                           SOURCE,MU_REFERENCE,MAX_COMPRESSION_FRACTION,CALIBRATION_FORCE_TOLERANCE)
from analysis.material.hyperfoam import Hyperfoam
from analysis.sponge.geometry import Sponge

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OUT=HERE/'outputs'
SCENARIOS=[('primary',10.,0.),('alpha20',20.,0.),('beta0125',10.,.125)]


def write_csv(name,rows):
    rows=list(rows)
    if not rows:return
    with (OUT/name).open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def parameter_row(name,fit,capacity):
    return dict(scenario=name,role='primary' if name=='primary' else 'assumption sensitivity',
                mu_Pa=fit.mu,alpha=fit.alpha,beta=fit.beta,tare_g=75,
                predicted_500_mm=1000*fit.predicted_m[0],predicted_1000_mm=1000*fit.predicted_m[1],
                residual_500_mm=1000*fit.residual_m[0],residual_1000_mm=1000*fit.residual_m[1],
                calibration_RMSE_mm=1000*fit.rmse_m,evaluations=fit.evaluations,
                lower_mu_Pa=fit.lower_mu,upper_mu_Pa=fit.upper_mu,success=fit.success,
                capacity_at_13mm_N=capacity)


def domain_row(name,engine,fit):
    s=engine.cap_state
    assert s.min_J>0 and s.free_residual<=CALIBRATION_FORCE_TOLERANCE*1.001
    return dict(scenario=name,alpha=fit.alpha,beta=fit.beta,reference_mu_Pa=MU_REFERENCE,
                maximum_compression_fraction=MAX_COMPRESSION_FRACTION,cap_compression_m=engine.cap,
                reference_capacity_N=s.top_reaction,calibrated_capacity_N=s.top_reaction*fit.mu/MU_REFERENCE,
                min_J=s.min_J,max_J=s.max_J,reference_free_residual_N=s.free_residual,termination=s.termination)


def protected_hashes():
    paths=itertools.chain((ROOT/'analysis').rglob('*'),(ROOT/'Videos').rglob('*'))
    return {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(paths) if p.is_file() and HERE not in p.parents and '__pycache__' not in p.parts}


def audit_state(label,mesh,force,state,mu,history_rows):
    assert mu>0 and 0<=state.displacement<=.020*MAX_COMPRESSION_FRACTION
    assert state.min_J>0 and state.termination=='converged_free_force_residual'
    # Scaled reference solves may have absolute residual scaled by mu/2000.
    assert state.free_residual<2e-6
    assert abs(state.top_reaction-force)<max(2e-6,2e-6*force)
    assert abs(state.bottom_reaction-state.top_reaction)<2e-6
    for i,h in enumerate(state.history):
        assert h['min_J']>0
        history_rows.append(dict(scenario=label,mesh=mesh,force_N=force,index=i,displacement_m=h.get('platen_displacement_m',state.displacement),min_J=h['min_J'],free_residual_N=h['free_residual_N']))
    return dict(scenario=label,mesh=mesh,force_N=force,compression_mm=state.displacement*1000,
                strain_yellow=state.displacement/.020,energy_J=state.energy,reaction_N=state.top_reaction,
                force_error_N=state.top_reaction-force,bottom_reaction_N=state.bottom_reaction,
                force_balance_N=state.top_reaction-state.bottom_reaction,free_residual_N=state.free_residual,
                min_J=state.min_J,max_J=state.max_J,iterations=state.iterations,termination=state.termination)


def run():
    OUT.mkdir(exist_ok=True);before=protected_hashes()
    obs=training_observations();forces=force_from_water([500,1000])
    protocol=dict(primary=dict(alpha=10,beta=0,fit_parameters=['mu_Pa']),sensitivity_scenarios=SCENARIOS[1:],
                  loss='equal-weight sum of squared displacement residuals in metres',tare_g=75,
                  water_density_g_ml=1,g_m_s2=9.81,yellow_height_m=.020,backing_height_m=.007,
                  fitting_cycles=['500ml/1','1000ml/1'],held_out_from_present_fit=['750ml/1','750ml/2'],
                  max_compression_fraction=MAX_COMPRESSION_FRACTION,reference_inner_force_tolerance_N=CALIBRATION_FORCE_TOLERANCE,fit_mesh=[1,1,1],verification_mesh=[2,2,2],
                  no_selection_using_750=True,validation_is_prospective=False,
                  source_csv_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest())
    (OUT/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
    engines={};fits={};parameters=[];histories=[];numeric=[];sens=[];domains=[]
    for name,alpha,beta in SCENARIOS:
        engine=FEMResponse(alpha,beta);fit=engine.fit(forces,obs)
        engines[name]=engine;fits[name]=fit
        parameters.append(parameter_row(name,fit,engine.capacity_reference*fit.mu/MU_REFERENCE))
        domains.append(domain_row(name,engine,fit))
        print(f'FIT {name}: mu={fit.mu:.6f} Pa; RMSE={fit.rmse_m*1000:.6f} mm',flush=True)
    # Persist all official fits BEFORE evaluation. No held-out error can feed fitting.
    write_csv('parameters.csv',parameters)
    write_csv('domain_checks.csv',domains)
    (OUT/'frozen_fits.json').write_text(json.dumps({k:asdict(v) for k,v in fits.items()},indent=2)+'\n')
    frozen_hash=hashlib.sha256((OUT/'frozen_fits.json').read_bytes()).hexdigest()
    with SOURCE.open(newline='',encoding='utf-8') as f:all_obs=list(csv.DictReader(f))
    residuals=[];metrics=[];mesh_checks=[];curves=[];conditional=[];mesh_fits=[]
    grid=np.unique(np.r_[np.linspace(0,11.5,24),forces,float(force_from_water(750)),6.5,9.5])
    for name,alpha,beta in SCENARIOS:
        fit=fits[name];engine=engines[name]
        for r in all_obs:
            force=float(force_from_water(float(r['video'].replace('ml',''))))
            state=engine.predict(force,fit.mu);measured=float(r['hold_compression_mm'])
            x=state.displacement*1000;allowance=.3+.1*measured
            split='calibration' if r['split']=='initial_fit' else 'held_out_from_FEM_fit' if r['video']=='750ml' else 'repeat_load'
            residuals.append(dict(model=name,video=r['video'],cycle=int(r['cycle']),split=split,
                                  force_N=force,observed_mm=measured,predicted_mm=x,residual_mm=x-measured,
                                  engineering_allowance_mm=allowance,within_allowance=abs(x-measured)<=allowance))
        for force in grid:
            state=engine.predict(float(force),fit.mu)
            row=audit_state(name,'1x1x1_scaled',float(force),state,fit.mu,histories)
            numeric.append(row);curves.append(dict(scenario=name,force_N=float(force),compression_mm=state.displacement*1000))
        assert np.all(np.diff([r['compression_mm'] for r in curves if r['scenario']==name])>0)
        # Independent direct-scale solves use actual calibrated material at both meshes.
        for subdivisions in [(1,1,1),(2,2,2)]:
            mesh='x'.join(map(str,subdivisions));s=Sponge(subdivisions=subdivisions,material=Hyperfoam(fit.mu,alpha,beta))
            s.solver.force_tolerance=CALIBRATION_FORCE_TOLERANCE
            for force in sorted([float(forces[0]),float(force_from_water(750)),float(forces[1]),6.5,9.5]):
                state=s.solve_force(force);numeric.append(audit_state(name,mesh+'_direct',force,state,fit.mu,histories))
                ref=engine.predict(force,fit.mu)
                assert abs(state.displacement-ref.displacement)<2e-8
                assert state.free_residual<=CALIBRATION_FORCE_TOLERANCE*1.001
                mesh_checks.append(dict(scenario=name,mesh=mesh,force_N=force,direct_compression_mm=state.displacement*1000,
                                        scaled_coarse_compression_mm=ref.displacement*1000,
                                        difference_mm=(state.displacement-ref.displacement)*1000))
                write_csv(f'{name}_{mesh}_F{force:.5f}_nodes.csv',
                          (dict(node=i,X_m=X[0],Y_m=X[1],Z_m=X[2],x_m=x[0],y_m=x[1],z_m=x[2]) for i,(X,x) in enumerate(zip(s.solver.X,state.positions))))
        for force,d in zip(forces,obs):
            state=engine.sponge.solve_displacement(float(d))
            conditional.append(dict(scenario=name,force_N=force,observed_mm=d*1000,
                                    exact_single_endpoint_mu_Pa=force*MU_REFERENCE/state.top_reaction))
        # Refit on the fine mesh too, rather than only comparing forward predictions.
        fine=FEMResponse(alpha,beta,(2,2,2));ff=fine.fit(forces,obs)
        mesh_fits.append(dict(scenario=name,coarse_mu_Pa=fit.mu,fine_mu_Pa=ff.mu,
                              mu_relative_difference=(ff.mu-fit.mu)/fit.mu,
                              coarse_RMSE_mm=fit.rmse_m*1000,fine_RMSE_mm=ff.rmse_m*1000))
        assert abs(ff.mu/fit.mu-1)<2e-5
        write_csv(f'{name}_fine_fit_trace.csv',fine.trace)
        print(f'CHECK {name}: direct solves, fine-mesh refit, monotonic curve PASS',flush=True)
    # Empirical baseline is the previously declared monotone table. Upper segment is
    # interpolation within the two fitting endpoints, lower segment is unvalidated.
    def baseline(force,endpoint=obs,ff=forces):
        if force<0 or force>ff[1]+1e-12:raise ValueError('No upper extrapolation of empirical baseline')
        return float(np.interp(force,[0,*ff],[0,*endpoint]))
    for r in all_obs:
        force=float(force_from_water(float(r['video'].replace('ml',''))));measured=float(r['hold_compression_mm'])
        pred=1000*baseline(force);split='calibration' if r['split']=='initial_fit' else 'held_out_from_FEM_fit' if r['video']=='750ml' else 'repeat_load'
        residuals.append(dict(model='empirical_interpolation',video=r['video'],cycle=int(r['cycle']),split=split,force_N=force,
                              observed_mm=measured,predicted_mm=pred,residual_mm=pred-measured,
                              engineering_allowance_mm=.3+.1*measured,within_allowance=abs(pred-measured)<=.3+.1*measured))
    write_csv('empirical_baseline_curve.csv',(dict(force_N=f,compression_mm=1000*baseline(f)) for f in np.unique(np.r_[np.linspace(0,forces[1],100),forces])))
    for model in [s[0] for s in SCENARIOS]+['empirical_interpolation']:
        for split in ['calibration','held_out_from_FEM_fit','repeat_load']:
            errs=[r['residual_mm'] for r in residuals if r['model']==model and r['split']==split]
            metrics.append(dict(model=model,split=split,n=len(errs),RMSE_mm=float(np.sqrt(np.mean(np.square(errs)))),MAE_mm=float(np.mean(np.abs(errs)))))
    # Training-only sensitivity refits. Shared tare is applied to both endpoints and query.
    scenarios=[]
    for tare in [50,100]:scenarios.append(('tare',f'shared_{tare}g',tare,obs,1.))
    for factor in [.9,1.1]:scenarios.append(('common_scale',f'all_videos_x{factor}',75,obs*factor,factor))
    for a,b in itertools.product([-.1,.1],repeat=2):scenarios.append(('differential_scale',f'low{1+a}_high{1+b}',75,obs*[1+a,1+b],1.))
    for a,b in itertools.product([-.3,.3],repeat=2):scenarios.append(('localization',f'low{a:+g}_high{b:+g}mm',75,obs+np.array([a,b])/1000,1.))
    allowance=.0003+.1*obs
    for tare,(a,b) in itertools.product([50,100],itertools.product([-1,1],repeat=2)):
        scenarios.append(('combined_engineering_corners',f'tare{tare}_low{a:+}_high{b:+}',tare,obs+allowance*[a,b],1.))
    for cycles in [(1,2),(2,1),(2,2)]:scenarios.append(('repeat_endpoints',f'cycles{cycles[0]}_{cycles[1]}',75,training_observations(cycles=cycles),1.))
    engine=engines['primary']
    held=[float(r['hold_compression_mm']) for r in all_obs if r['video']=='750ml']
    for group,label,tare,xx,evaluation_scale in scenarios:
        f=force_from_water([500,1000],tare);fit=engine.fit(f,xx)
        q=float(force_from_water(750,tare));state=engine.predict(q,fit.mu)
        # Common scale also applies to held-out optical measurements; differential
        # endpoint scenarios below retain the 750 scale explicitly as a separate axis.
        eval_scales=[.9,1.,1.1] if group=='differential_scale' else [evaluation_scale]
        for es in eval_scales:
            errors=state.displacement*1000-np.asarray(held)*es
            sens.append(dict(group=group,case=label,tare_g=tare,endpoint_low_mm=xx[0]*1000,endpoint_high_mm=xx[1]*1000,
                             evaluation_scale=es,mu_Pa=fit.mu,calibration_RMSE_mm=fit.rmse_m*1000,
                             prediction_750_mm=state.displacement*1000,error_750_cycle1_mm=errors[0],error_750_cycle2_mm=errors[1],
                             holdout_RMSE_mm=float(np.sqrt(np.mean(errors**2))),min_J=state.min_J,
                             baseline_750_mm=float(np.mean(xx))*1000,
                             baseline_holdout_RMSE_mm=float(np.sqrt(np.mean((np.mean(xx)*1000-np.asarray(held)*es)**2)))))
        numeric.append(audit_state('sensitivity_'+label,'1x1x1_scaled',q,state,fit.mu,histories))
        for force in f:numeric.append(audit_state('sensitivity_'+label,'1x1x1_scaled',float(force),engine.predict(float(force),fit.mu),fit.mu,histories))
        print(f'SENS {group}/{label}: mu={fit.mu:.3f} Pa',flush=True)
    # Local identifiability diagnostic, no additional parameter fitting. The two-row
    # Jacobian uses dimensionless perturbation coordinates (1% mu, 1 alpha, .01 beta).
    mu=fits['primary'].mu
    base=np.asarray(fits['primary'].predicted_m)
    deriv_mu=np.array([(engine.predict(f,mu*1.001).displacement-engine.predict(f,mu*.999).displacement)/.002*.01 for f in forces])
    ap=FEMResponse(10.1,0);am=FEMResponse(9.9,0);bp=FEMResponse(10,.001)
    deriv_alpha=np.array([(ap.predict(f,mu).displacement-am.predict(f,mu).displacement)/.2 for f in forces])
    deriv_beta=np.array([(bp.predict(f,mu).displacement-base[i])/.001*.01 for i,f in enumerate(forces)])
    jac=np.column_stack([deriv_mu,deriv_alpha,deriv_beta]);_,singular,vh=np.linalg.svd(jac,full_matrices=True)
    write_csv('local_identifiability.csv',(dict(force_N=f,dx_mm_per_1percent_mu=jac[i,0]*1000,dx_mm_per_unit_alpha=jac[i,1]*1000,dx_mm_per_001_beta=jac[i,2]*1000) for i,f in enumerate(forces)))
    write_csv('predictions.csv',residuals);write_csv('metrics.csv',metrics);write_csv('fem_curve.csv',curves)
    write_csv('numerical_checks.csv',numeric);write_csv('mesh_checks.csv',mesh_checks);write_csv('mesh_refits.csv',mesh_fits)
    write_csv('single_endpoint_scales.csv',conditional);write_csv('sensitivity.csv',sens);write_csv('iteration_checks.csv',histories)
    write_csv('force_conversion.csv',(dict(water_ml=v,tare_g=t,force_N=float(force_from_water(v,t))) for t in [50,75,100] for v in [500,750,1000]))
    for name,engine in engines.items():write_csv(f'{name}_fit_trace.csv',engine.trace)
    for label in dict.fromkeys(r['scenario'] for r in numeric):
        byforce={r['force_N']:r['compression_mm'] for r in numeric if r['scenario']==label}
        pairs=sorted(byforce.items())
        assert all(b[1]>a[1] for a,b in zip(pairs,pairs[1:])),f'Nonmonotonic scenario: {label}'
    assert frozen_hash==hashlib.sha256((OUT/'frozen_fits.json').read_bytes()).hexdigest()
    plot_results(curves,residuals,sens,fits)
    assert before==protected_hashes(),'A protected prior file changed'
    summary=dict(status='PASS',primary_mu_Pa=mu,calibration_RMSE_mm=fits['primary'].rmse_m*1000,
                 primary_750_mm=next(r['predicted_mm'] for r in residuals if r['model']=='primary' and r['video']=='750ml'),
                 max_free_residual_N=max(r['free_residual_N'] for r in numeric),
                 max_direct_free_residual_N=max(r['free_residual_N'] for r in numeric if r['mesh'].endswith('_direct')),
                 max_force_error_N=max(abs(r['force_error_N']) for r in numeric),max_force_balance_N=max(abs(r['force_balance_N']) for r in numeric),
                 min_final_J=min(r['min_J'] for r in numeric),min_recorded_J=min(r['min_J'] for r in histories),
                 max_mesh_or_scaling_displacement_difference_mm=max(abs(r['difference_mm']) for r in mesh_checks),
                 audited_states=len(numeric),history_rows=len(histories),sensitivity_refits=len(scenarios),sensitivity_records=len(sens),
                 local_jacobian_rank=int(np.linalg.matrix_rank(jac)),local_singular_values_m=singular.tolist(),local_null_vector_scaled_coordinates=vh[-1].tolist(),
                 protected_files_unchanged=len(before),frozen_fits_sha256=frozen_hash,numpy=np.__version__,scipy=scipy.__version__)
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    (OUT/'preserved_sha256.json').write_text(json.dumps(before,indent=2)+'\n')
    print(json.dumps(summary,indent=2),flush=True)


def plot_results(curves,residuals,sens,fits):
    colors=dict(primary='#1768ac',alpha20='#b25d05',beta0125='#8c4799')
    fig,ax=plt.subplots(figsize=(9.5,6.1))
    for name,_,_ in SCENARIOS:
        rr=[r for r in curves if r['scenario']==name]
        ax.plot([r['force_N'] for r in rr],[r['compression_mm'] for r in rr],color=colors[name],lw=2 if name=='primary' else 1.3,
                label=f'FEM {name}: mu = {fits[name].mu/1000:.3f} kPa',ls='-' if name=='primary' else '--')
    with (OUT/'empirical_baseline_curve.csv').open() as f:bb=list(csv.DictReader(f))
    ax.plot([float(r['force_N']) for r in bb],[float(r['compression_mm']) for r in bb],color='#444444',ls=':',label='Empirical monotone table (loaded interval: chord)')
    for split,marker,color,title in [('calibration','o','black','Calibration: first 500/1000 cycles'),('held_out_from_FEM_fit','D','#d53939','750 ml: held out from this FEM fit'),('repeat_load','s','#548235','Repeated 500/1000 loads')]:
        rr=[r for r in residuals if r['model']=='primary' and r['split']==split]
        ax.errorbar([r['force_N'] for r in rr],[r['observed_mm'] for r in rr],yerr=[r['engineering_allowance_mm'] for r in rr],fmt=marker,ms=6,color=color,capsize=3,ls='none',label=title)
    ax.set(xlabel='Assumed incremental supported force (N)',ylabel='Compression from card-on-sponge baseline (mm)',xlim=(0,11.7),ylim=(0,13.2))
    ax.grid(alpha=.2);ax.legend(fontsize=8,loc='upper left')
    ax.set_title('Stage 5: 20 mm yellow layer, rigid backing, full-face platen\nError bars: engineering allowances, not confidence intervals',fontsize=11)
    fig.tight_layout();fig.savefig(OUT/'force_compression.png',dpi=170);plt.close(fig)
    groups=list(dict.fromkeys(r['group'] for r in sens))
    fig,axs=plt.subplots(1,2,figsize=(12,5.4))
    for ax,key,title,base in [(axs[0],'mu_Pa','Effective mu (kPa)',fits['primary'].mu),(axs[1],'prediction_750_mm','750 ml prediction (mm)',next(r['predicted_mm'] for r in residuals if r['model']=='primary' and r['video']=='750ml') )]:
        divisor=1000 if key=='mu_Pa' else 1
        for i,g in enumerate(groups):
            values=np.array([r[key] for r in sens if r['group']==g])/divisor
            ax.plot([values.min(),values.max()],[i,i],lw=4,alpha=.55,color='#1768ac');ax.scatter(values,[i]*len(values),s=13,color='#1768ac')
        ax.axvline(base/divisor,color='black',ls='--',label='Primary nominal fit')
        ax.set(yticks=range(len(groups)),yticklabels=[g.replace('_',' ') for g in groups],xlabel=title);ax.invert_yaxis();ax.grid(axis='x',alpha=.2)
    axs[0].legend(fontsize=8);fig.suptitle('Training-input sensitivity refits at alpha = 10, beta = 0\nDeterministic scenarios; ranges are not confidence intervals',fontsize=11)
    fig.tight_layout();fig.savefig(OUT/'input_sensitivity.png',dpi=170);plt.close(fig)
    fig,axs=plt.subplots(1,2,figsize=(10,4.8))
    labels=[s[0] for s in SCENARIOS]
    axs[0].bar(labels,[fits[n].mu/1000 for n in labels],color=[colors[n] for n in labels]);axs[0].set(ylabel='Effective mu (kPa)')
    for split,offset,color in [('calibration',-.18,'#1768ac'),('held_out_from_FEM_fit',.18,'#d53939')]:
        values=[]
        for name in labels:
            e=[r['residual_mm'] for r in residuals if r['model']==name and r['split']==split];values.append(np.sqrt(np.mean(np.square(e))))
        axs[1].bar(np.arange(3)+offset,values,.35,label=split.replace('_',' '),color=color)
    axs[1].set(xticks=range(3),xticklabels=labels,ylabel='RMSE (mm)');axs[1].legend(fontsize=8)
    fig.suptitle('Fixed constitutive assumptions; each scenario fits only mu\nHeld-out errors are reported, never used to choose a scenario',fontsize=11)
    fig.tight_layout();fig.savefig(OUT/'constitutive_sensitivity.png',dpi=170);plt.close(fig)


if __name__=='__main__':run()
