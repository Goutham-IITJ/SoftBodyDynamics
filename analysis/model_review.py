"""Review empirical equilibrium laws; preserve extraction and original selection outputs."""
from pathlib import Path
import hashlib,json,itertools
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
HERE=Path(__file__).resolve().parent
OUT=HERE/'model_review'; OUT.mkdir(exist_ok=True)
paths=list((HERE/'outputs').rglob('*.csv'))+list((HERE/'model_selection').glob('*.csv'))
hashes={str(p.relative_to(HERE)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
d=pd.read_csv(HERE/'model_selection/observations.csv')
summary=pd.read_csv(HERE/'outputs/cycle_summary.csv')
for r in d.itertuples():
    assert abs(r.x_mm-summary[(summary.video==r.video)&(summary.cycle==r.cycle)].hold_compression_mm.iloc[0])<1e-10
train=d[d.split=='initial_fit'].sort_values('force_N')
f=train.force_N.to_numpy(); x=train.x_mm.to_numpy(); u=train.u_mm.to_numpy()
def estimates(f,x):
    w=1/(.3+.1*x)**2
    compliance=np.sum(w*f*x)/np.sum(w*f*f)
    q=np.sum(w*f*f*x)/np.sum(w*f**4)
    n=np.log(x[1]/x[0])/np.log(f[1]/f[0]); a=x[0]/f[0]**n
    return compliance,q,a,n
def predict(f,x,query):
    b,q,a,n=estimates(f,x)
    return dict(linear=b*query,quadratic=q*query**2,local_interpolation=x[0]+(x[1]-x[0])*(query-f[0])/(f[1]-f[0]),power=a*query**n)
res=[]
for r in d.itertuples():
    for model,pred in predict(f,x,r.force_N).items():
        res.append(dict(model=model,video=r.video,cycle=r.cycle,split=r.split,measured_mm=r.x_mm,predicted_mm=pred,residual_mm=pred-r.x_mm,allowance_mm=r.u_mm,within_allowance=abs(pred-r.x_mm)<=r.u_mm))
res=pd.DataFrame(res);res.to_csv(OUT/'cycle_residuals.csv',index=False)
repeat=[]
for name,g in d.groupby('video',sort=False):
    a,b=g.sort_values('cycle').x_mm; mean=(a+b)/2
    repeat.append(dict(video=name,cycle1_mm=a,cycle2_mm=b,mean_mm=mean,difference_cycle2_minus1_mm=b-a,range_mm=abs(b-a),half_range_mm=abs(b-a)/2,sample_sd_mm=abs(b-a)/np.sqrt(2),sample_cv_percent=100*abs(b-a)/np.sqrt(2)/mean,range_percent_mean=100*abs(b-a)/mean))
pd.DataFrame(repeat).to_csv(OUT/'repeatability.csv',index=False)
metrics=[]
for (model,split),g in res.groupby(['model','split']):metrics.append(dict(model=model,split=split,rmse_mm=np.sqrt(np.mean(g.residual_mm**2)),mae_mm=np.abs(g.residual_mm).mean()))
pd.DataFrame(metrics).to_csv(OUT/'metrics.csv',index=False)
sens=[]
for lowcycle,highcycle in itertools.product([1,2],repeat=2):
    xx=np.array([d[(d.video=='500ml')&(d.cycle==lowcycle)].x_mm.iloc[0],d[(d.video=='1000ml')&(d.cycle==highcycle)].x_mm.iloc[0]])
    for tare in [50,75,100]:
        ff=(np.array([500,1000])+tare)*.00981; query=(750+tare)*.00981
        for model,pred in predict(ff,xx,query).items():
            sens.append(dict(low_cycle=lowcycle,high_cycle=highcycle,tare_g=tare,model=model,prediction_750_mm=pred,diagnostic_only=lowcycle!=1 or highcycle!=1))
pd.DataFrame(sens).to_csv(OUT/'endpoint_repeat_tare_sensitivity.csv',index=False)
# Evaluate correlation honestly: the same scale affects both prediction and measurement.
cal=[]
held=d[d.video=='750ml'].sort_values('cycle').x_mm.to_numpy()
for mode in ['common','differential']:
    scales=[(s,s,s) for s in [.9,1,1.1]] if mode=='common' else itertools.product([.9,1,1.1],repeat=3)
    for sl,sh,sm in scales:
        for model,pred in predict(f,x*np.array([sl,sh]),(750+75)*.00981).items():
            y=held*sm; errors=pred-y
            cal.append(dict(mode=mode,scale_low=sl,scale_high=sh,scale_mid=sm,model=model,prediction_mm=pred,error_cycle1_mm=errors[0],error_cycle2_mm=errors[1],holdout_rmse_mm=np.sqrt(np.mean(errors**2))))
pd.DataFrame(cal).to_csv(OUT/'correlated_calibration_sensitivity.csv',index=False)
# Endpoint localization perturbation envelope (not confidence interval).
loc=[]
for e0,e1 in itertools.product([-.3,0,.3],repeat=2):
    for model,pred in predict(f,x+np.array([e0,e1]),d[d.video=='750ml'].force_N.iloc[0]).items():loc.append(dict(endpoint_low_shift_mm=e0,endpoint_high_shift_mm=e1,model=model,prediction_750_mm=pred))
pd.DataFrame(loc).to_csv(OUT/'localization_sensitivity.csv',index=False)
b,q,a,n=estimates(f,x)
kt=[dict(force_N=ff,compression_mm=q*ff**2,tangent_stiffness_N_mm=1/(2*q*ff)) for ff in [f[0],8.09325,f[1]]]
pd.DataFrame(kt).to_csv(OUT/'quadratic_tangent_stiffness.csv',index=False)
fig,axs=plt.subplots(1,2,figsize=(12,5)); grid=np.linspace(f[0],f[1],200)
for model in ['linear','quadratic','local_interpolation','power']:
    axs[0].plot(grid,[predict(f,x,F)[model] for F in grid],label=model)
    r=res[(res.model==model)&(res.video=='750ml')];axs[1].plot([1,2],r.residual_mm,'o-',label=model)
for r in d.itertuples():axs[0].errorbar(r.force_N,r.x_mm,yerr=r.u_mm,fmt='s' if r.cycle==2 else 'o',color='black' if r.split=='initial_fit' else 'gray',capsize=3)
axs[0].set(xlabel='Assumed incremental force [N]',ylabel='Compression [mm]');axs[1].set(xlabel='Held-out cycle',ylabel='Predicted minus measured [mm]',xticks=[1,2]);axs[1].axhline(0,color='gray')
for ax in axs:ax.legend();ax.grid(alpha=.2)
fig.suptitle('Original cycle-1 endpoints only; evaluation cycles never used in the curves')
fig.tight_layout();fig.savefig(OUT/'comparison.png',dpi=160);plt.close(fig)
assert all(hashlib.sha256((HERE/p).read_bytes()).hexdigest()==h for p,h in hashes.items())
(OUT/'provenance.json').write_text(json.dumps(dict(inputs_unchanged=True,input_sha256=hashes,script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()),indent=2))
print(pd.DataFrame(repeat).to_string(index=False));print(pd.DataFrame(metrics).to_string(index=False));print(res.to_string(index=False));print('endpoint diagnostics',pd.DataFrame(sens).groupby('model').prediction_750_mm.agg(['min','max']).to_string());print('localization',pd.DataFrame(loc).groupby('model').prediction_750_mm.agg(['min','max']).to_string()); print('tangent',kt)
