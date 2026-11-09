"""Phase 3: static model selection and identifiability diagnostics only.
Run python analysis/model_selection.py. Reads Phase 2 data; writes model_selection/.
"""
import hashlib
import itertools
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar, lsq_linear
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE=Path(__file__).resolve().parent
SOURCE=HERE/'outputs'; OUT=HERE/'model_selection'; OUT.mkdir(exist_ok=True)
cfg=json.loads((HERE/'config.json').read_text())
inputs=[HERE/'config.json',SOURCE/'cycle_summary.csv']+list(SOURCE.glob('*/measurements.csv'))+list(SOURCE.glob('*/markers.csv'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before={str(p.relative_to(HERE)):sha(p) for p in inputs}
summary=pd.read_csv(SOURCE/'cycle_summary.csv')
records=[]; frames={}
for name,conf in cfg['videos'].items():
    d=pd.read_csv(SOURCE/name/'measurements.csv'); frames[name]=d
    for cycle in conf['cycles']:
        s=d[d.time_s.between(*cycle['hold'])]
        x=float(s.compression_mm.median())
        old=summary[(summary.video==name)&(summary.cycle==cycle['id'])].iloc[0]
        assert abs(x-old.hold_compression_mm)<1e-10
        records.append(dict(video=name,cycle=cycle['id'],split=cycle['split'],water_g=conf['water_g'],
            hold_start_s=cycle['hold'][0],hold_end_s=cycle['hold'][1],first_frame=int(s.frame.iloc[0]),last_frame=int(s.frame.iloc[-1]),samples=len(s),
            x_mm=x,u_mm=.3+.1*abs(x),force_N=(conf['water_g']+75)*.00981))
data=pd.DataFrame(records); data.to_csv(OUT/'observations.csv',index=False)
train=data[data.split=='initial_fit']; assert set(train.video)=={'500ml','1000ml'} and len(train)==2
F=train.force_N.to_numpy(); X=train.x_mm.to_numpy(); U=train.u_mm.to_numpy()
FREF=8.0  # fixed units convention; not a fitted parameter

def fit(force,x,u,kind):
    n=1. if kind=='A_linear' else 2.
    if kind=='C_power': n=float(np.log(x[1]/x[0])/np.log(force[1]/force[0]))
    assert n>0
    z=(force/FREF)**n
    a=float(np.sum(z*x/u**2)/np.sum(z*z/u**2))
    return a,n

models=['A_linear','C_power','C_square']
parameters={m:fit(F,X,U,m) for m in models}
predictions=[]; metrics=[]
for model,(a,n) in parameters.items():
    for r in data.itertuples():
        xp=a*(r.force_N/FREF)**n; fp=FREF*(r.x_mm/a)**(1/n)
        predictions.append(dict(model=model,video=r.video,cycle=r.cycle,split=r.split,measured_x_mm=r.x_mm,force_N=r.force_N,
            predicted_x_mm=xp,x_error_mm=xp-r.x_mm,predicted_force_at_measured_x_N=fp,force_error_N=fp-r.force_N,
            measurement_allowance_mm=r.u_mm,within_measurement_allowance=abs(xp-r.x_mm)<=r.u_mm))
    rows=pd.DataFrame(predictions); rows=rows[rows.model==model]
    for split,g in rows.groupby('split'):
        metrics.append(dict(model=model,split=split,rmse_mm=float(np.sqrt(np.mean(g.x_error_mm**2))),mae_mm=float(np.abs(g.x_error_mm).mean()),max_abs_error_mm=float(np.abs(g.x_error_mm).max())))
pd.DataFrame(predictions).to_csv(OUT/'predictions.csv',index=False); pd.DataFrame(metrics).to_csv(OUT/'metrics.csv',index=False)
paramrows=[]
for model,(a,n) in parameters.items():
    paramrows.append(dict(model=model,amplitude_at_8N_mm=a,exponent=n,fitted_parameters=2 if model=='C_power' else 1,
                          stiffness_N_per_mm=FREF/a if n==1 else np.nan,square_coefficient_mm_per_N2=a/FREF**2 if n==2 else np.nan))
pd.DataFrame(paramrows).to_csv(OUT/'parameters.csv',index=False)

# Shared tare changes all forces coherently. Never fit using held-out displacements.
sens=[]
for tare in np.linspace(50,100,51):
    force=(train.water_g.to_numpy()+tare)*.00981
    for model in models:
        a,n=fit(force,X,U,model)
        sens.append(dict(tare_g=tare,model=model,a_mm=a,n=n,k_N_per_mm=FREF/a if n==1 else np.nan,
                         q_mm_per_N2=a/FREF**2 if n==2 else np.nan,prediction_750_mm=a*(((750+tare)*.00981)/FREF)**n))
pd.DataFrame(sens).to_csv(OUT/'tare_sensitivity.csv',index=False)

# Deterministic sensitivity corners, NOT random errors or confidence intervals.
# Shared scale is correlated; differential per-video scale is a stress test.
scenarios=[]
for mode in ['shared_scale','differential_scale']:
    scales=([(.9,.9),(1.,1.),(1.1,1.1)] if mode=='shared_scale' else itertools.product([.9,1.,1.1],repeat=2))
    for scales_pair in scales:
        for shifts in itertools.product([-.3,0.,.3],repeat=2):
            xt=X*np.array(scales_pair)+np.array(shifts)
            for tare in [50.,75.,100.]:
                force=(train.water_g.to_numpy()+tare)*.00981
                for model in models:
                    a,n=fit(force,xt,.3+.1*xt,model)
                    scenarios.append(dict(mode=mode,model=model,tare_g=tare,scale_500=scales_pair[0],scale_1000=scales_pair[1],
                        offset_500_mm=shifts[0],offset_1000_mm=shifts[1],a_mm=a,n=n,k_N_per_mm=FREF/a if n==1 else np.nan,
                        q_mm_per_N2=a/FREF**2 if n==2 else np.nan,prediction_750_mm=a*(((750+tare)*.00981)/FREF)**n))
pd.DataFrame(scenarios).to_csv(OUT/'calibration_sensitivity.csv',index=False)

# Interval feasibility for linear compliance: the two training intervals must intersect.
feas=[]
for tare in [50,75,100]:
    for mode in ['nominal','shared_scale','differential_scale']:
        choices=[(1,1)] if mode=='nominal' else ([(.9,.9),(1.1,1.1)] if mode=='shared_scale' else list(itertools.product([.9,1.1],repeat=2)))
        for scales in choices:
            forces=(train.water_g.to_numpy()+tare)*.00981
            lo=(X*np.array(scales)-.3)/forces; hi=(X*np.array(scales)+.3)/forces
            feas.append(dict(mode=mode,tare_g=tare,scale_500=scales[0],scale_1000=scales[1],compliance_lower_mm_N=max(lo),compliance_upper_mm_N=min(hi),feasible=max(lo)<=min(hi)))
pd.DataFrame(feas).to_csv(OUT/'linear_interval_feasibility.csv',index=False)

# Recovery profiles: only fitting cycles. Descriptive timescale identifiability,
# not a c estimate. Each clip has free amplitude and baseline offset.
profiles=[]
for r in train.itertuples():
    conf=next(c for c in cfg['videos'][r.video]['cycles'] if c['id']==r.cycle)
    stop=next((c['contact'][0] for c in cfg['videos'][r.video]['cycles'] if c['id']>r.cycle),frames[r.video].time_s.iloc[-1])
    d=frames[r.video]; d=d[(d.time_s>conf['separation'][1])&(d.time_s<stop)]
    t=d.time_s.to_numpy()-conf['separation'][1]; y=d.compression_mm.to_numpy()
    weights=np.gradient(t); weights/=weights.sum()
    for tau in np.geomspace(.005,30,160):
        matrix=np.column_stack([np.exp(-t/tau),np.ones_like(t)])
        sol=lsq_linear(matrix*np.sqrt(weights[:,None]),y*np.sqrt(weights),bounds=([0,-.3],[max(y[:10])+.3,1.5]))
        rmse=float(np.sqrt(np.sum(weights*(matrix@sol.x-y)**2)))
        profiles.append(dict(video=r.video,cycle=r.cycle,tau_s=tau,amplitude_mm=sol.x[0],offset_mm=sol.x[1],time_weighted_rmse_mm=rmse,within_practical_resolution=rmse<=.3))
pd.DataFrame(profiles).to_csv(OUT/'recovery_profile.csv',index=False)

fig,axes=plt.subplots(1,2,figsize=(12,5))
grid=np.linspace(0,11,300)
for model,(a,n) in parameters.items():
    axes[0].plot(a*(grid/FREF)**n,grid,label=model)
    axes[1].plot(grid,a*(grid/FREF)**n,label=model)
for r in data.itertuples():
    color='C1' if r.video=='750ml' else ('black' if r.split=='initial_fit' else 'C2')
    marker='o' if r.cycle==1 else 's'
    axes[0].errorbar(r.x_mm,r.force_N,xerr=r.u_mm,yerr=.24525,fmt=marker,color=color)
    axes[1].errorbar(r.force_N,r.x_mm,xerr=.24525,yerr=r.u_mm,fmt=marker,color=color)
axes[0].set(xlabel='Compression [mm]',ylabel='Assumed incremental force [N]'); axes[1].set(xlabel='Assumed force [N]',ylabel='Compression [mm]')
for ax in axes: ax.legend(); ax.grid(alpha=.2)
fig.suptitle('Training: black; intermediate-load holdout: orange; repetitions: green\nBars are engineering allowances, not confidence intervals; curves outside training span are extensions')
fig.tight_layout(); fig.savefig(OUT/'force_compression.png',dpi=160); plt.close(fig)

fig,axes=plt.subplots(1,2,figsize=(12,5)); pr=pd.DataFrame(predictions)
for model,g in pr.groupby('model'):
    axes[0].scatter(g.measured_x_mm,g.predicted_x_mm,label=model)
    axes[1].scatter(g.force_N,g.x_error_mm,label=model)
axes[0].plot([0,13],[0,13],'k--'); axes[0].set(xlabel='Measured compression [mm]',ylabel='Predicted compression [mm]')
axes[1].axhline(0,color='k',ls='--'); axes[1].set(xlabel='Assumed force [N]',ylabel='Predicted minus measured [mm]')
for ax in axes: ax.legend(); ax.grid(alpha=.2)
fig.tight_layout(); fig.savefig(OUT/'predictions_residuals.png',dpi=160); plt.close(fig)
fig,axes=plt.subplots(1,2,figsize=(12,5)); se=pd.DataFrame(sens)
for model,g in se.groupby('model'):
    axes[0].plot(g.tare_g,g.prediction_750_mm,label=model)
    axes[1].plot(g.tare_g,g.a_mm,label=model)
axes[0].set(xlabel='Shared bottle tare [g]',ylabel='750 ml prediction [mm]'); axes[1].set(xlabel='Shared bottle tare [g]',ylabel='Compression amplitude at 8 N [mm]')
for ax in axes: ax.legend(); ax.grid(alpha=.2)
fig.tight_layout(); fig.savefig(OUT/'tare_sensitivity.png',dpi=160); plt.close(fig)
fig,ax=plt.subplots(figsize=(8,4)); pro=pd.DataFrame(profiles)
for name,g in pro.groupby('video'):ax.semilogx(g.tau_s,g.time_weighted_rmse_mm,label=name+' cycle 1')
ax.axhline(.3,color='k',ls='--',label='practical image resolution'); ax.set(xlabel='Profiled time constant [s]',ylabel='Time-weighted recovery RMSE [mm]'); ax.legend(); ax.grid(alpha=.2)
fig.tight_layout(); fig.savefig(OUT/'recovery_identifiability.png',dpi=160); plt.close(fig)
after={str(p.relative_to(HERE)):sha(p) for p in inputs}; assert before==after
(OUT/'provenance.json').write_text(json.dumps(dict(inputs_unchanged=True,input_sha256=after,script_sha256=sha(Path(__file__)),fit_split='initial_fit only',reference_force_N=FREF,loss='sum(((prediction-observation)/(.3+.1*abs(observation)))**2); each cycle one datum; allowances not Gaussian sigma'),indent=2))
print(pd.DataFrame(paramrows).to_string(index=False)); print(pr.to_string(index=False)); print(pd.DataFrame(metrics).to_string(index=False))
print('tare ranges',se.groupby('model')[['a_mm','n','prediction_750_mm']].agg(['min','max']).to_string())
print('calibration ranges',pd.DataFrame(scenarios).groupby(['mode','model'])[['a_mm','n','prediction_750_mm']].agg(['min','max']).to_string())
print('linear feasible?',pd.DataFrame(feas).groupby('mode').feasible.any().to_dict())
print('tau profile',pro.groupby('video').agg(rmse_min=('time_weighted_rmse_mm','min'),rmse_max=('time_weighted_rmse_mm','max'),all_accepted=('within_practical_resolution','all')).to_string())
