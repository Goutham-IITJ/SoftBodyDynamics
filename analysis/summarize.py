"""Create auditable summary tables and figures from extraction CSVs; no model fits."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from extract import CFG, OUT

forces=[]; cycles=[]; qualities=[]; timing=[]; frames={}
for name,conf in CFG['videos'].items():
    path=OUT/name
    d=pd.read_csv(path/'measurements.csv'); frames[name]=d
    m=pd.read_csv(path/'markers.csv')
    cal=json.loads((path/'calibration.json').read_text())
    meta=json.loads((path/'metadata.json').read_text())
    fig,axs=plt.subplots(2,1,figsize=(11,6),sharex=True)
    poly=cal['vertical_y_to_mm_polynomial']
    origin=np.polyval(poly,cal['baseline_measurements']['plate_center_y_px'])
    axs[0].plot(d.time_s,np.polyval(poly,d.bottle_bottom_y_px)-origin,label='visible bottle-bottom proxy')
    axs[0].plot(d.time_s,d.plate_translation_mm,label='card center')
    axs[0].set_ylabel('Downward position [mm]'); axs[0].legend()
    axs[1].plot(d.time_s,d.bottle_plate_gap_mm,label='apparent gap proxy (not contact ground truth)')
    axs[1].set(xlabel='Presentation time [s]',ylabel='Gap [ruler-equivalent mm]'); axs[1].legend()
    for c in conf['cycles']:
        for ax in axs: ax.axvspan(*c['separation'],color='orange',alpha=.3); ax.grid(alpha=.2)
    fig.suptitle(name+': bottle motion; orange = manually reviewed separation bracket')
    fig.tight_layout(); fig.savefig(path/'bottle_motion.png',dpi=150); plt.close(fig)
    timing.append({'video':name,**{k:meta[k] for k in ['width','height','decoded_frames','reported_fps','last_timestamp_s','duration_estimate_s','median_interval_s','max_interval_s','intervals_over_25ms','nonmonotonic_intervals']}})
    force={'video':name,'water_mass_assumed_g':conf['water_g'],'tare_assumed_g':75,'tare_low_g':50,'tare_high_g':100,'area_assumed_m2':.00365,'force_measured':False}
    for label,tare in zip(['low','nominal','high'],CFG['bottle_tare_g']):
        force[f'mass_{label}_kg']=(conf['water_g']+tare)/1000
        force[f'force_{label}_N']=force[f'mass_{label}_kg']*9.81
        force[f'pressure_{label}_Pa']=force[f'force_{label}_N']/.00365
    forces.append(force)
    base=cal['baseline_measurements']
    quality={'video':name,'ruler_mean_px_mm':cal['pixels_per_mm_original'],'vertical_calibration_residual_mm':cal['vertical_calibration_rms_mm'],
             'baseline_height_mm':base['height_mm'],'baseline_yellow_mm':base['yellow_thickness_mm'],'baseline_green_mm':base['green_thickness_mm'],
             'baseline_width_ruler_equivalent_mm':base['silhouette_width_mm'],'baseline_height_sd_mm':base['height_noise_sd_mm'],
             'registration_rms_median_px':d.registration_rms_px.median(),'registration_rms_max_px':d.registration_rms_px.max(),
             'camera_dx_range_px':d.camera_dx_px.max()-d.camera_dx_px.min(),'camera_dy_range_px':d.camera_dy_px.max()-d.camera_dy_px.min(),
             'camera_rotation_range_deg':d.camera_rotation_deg.max()-d.camera_rotation_deg.min(),'camera_scale_range_percent':(d.camera_scale.max()-d.camera_scale.min())*100,
             'marker_all_valid_fraction':m.valid.mean(),'registration_failed_frames':meta['registration_failed_frames']}
    for mid in range(1,10): quality[f'marker_{mid}_valid_fraction']=m.loc[m.marker_id==mid,'valid'].mean()
    qualities.append(quality)
    for c in conf['cycles']:
        hold=d[d.time_s.between(*c['hold'])]
        end=next((n['contact'][0] for n in conf['cycles'] if n['id']>c['id']),d.time_s.iloc[-1])
        recovery=d[(d.time_s>c['separation'][1])&(d.time_s<end)]
        early=recovery[recovery.time_s<c['separation'][1]+.15]
        late=recovery[recovery.time_s>end-.3]
        pre=d[d.time_s.between(c['contact'][0]-.4,c['contact'][0]-.1)]
        record={'video':name,'cycle':c['id'],'split':c['split'],'hold_start_s':c['hold'][0],'hold_end_s':c['hold'][1],
                'hold_start_frame':int(hold.frame.iloc[0]),'hold_end_frame':int(hold.frame.iloc[-1]),'hold_samples':len(hold),
                'separation_earliest_s':c['separation'][0],'separation_latest_s':c['separation'][1],
                'separation_earliest_frame':int(d.loc[d.time_s>=c['separation'][0],'frame'].iloc[0]),
                'separation_latest_frame':int(d.loc[d.time_s>=c['separation'][1],'frame'].iloc[0]),
                'recovery_end_s':end,'free_recovery_window_s':end-c['separation'][1],'free_recovery_samples':len(recovery),
                'precycle_residual_compression_mm':pre.compression_mm.median(),
                'early_free_compression_mm':early.compression_mm.median(),'late_free_compression_mm':late.compression_mm.median(),
                'post_separation_height_change_mm':early.compression_mm.median()-late.compression_mm.median()}
        for col in ['compression_mm','yellow_compression_mm','green_compression_mm','plate_translation_mm','plate_rotation_from_baseline_deg','plate_curve_p90_mm','marker_middle_width_change_mm']:
            record['hold_'+col]=hold[col].median()
        record['hold_compression_p05_mm']=hold.compression_mm.quantile(.05)
        record['hold_compression_p95_mm']=hold.compression_mm.quantile(.95)
        record['plate_force_window_motion_range_mm']=hold.plate_translation_mm.quantile(.95)-hold.plate_translation_mm.quantile(.05)
        cycles.append(record)
for filename,records in [('force_pressure_table.csv',forces),('cycle_summary.csv',cycles),('measurement_quality.csv',qualities),('video_metadata.csv',timing)]:
    pd.DataFrame(records).to_csv(OUT/filename,index=False)

fig,axes=plt.subplots(2,1,figsize=(11,8))
for name,d in frames.items():
    axes[0].plot(d.time_s,d.compression_mm,label=name)
axes[0].set(xlabel='Presentation time [s]',ylabel='Compression from card-only baseline [mm]'); axes[0].legend(); axes[0].grid(alpha=.2)
table=pd.DataFrame(cycles)
colors={'500ml':'C0','750ml':'C1','1000ml':'C2'}
for row in cycles:
    force=next(f for f in forces if f['video']==row['video'])
    y=row['hold_compression_mm']; unc=.3+CFG['scale_systematic_fraction_assumed']*abs(y)
    axes[1].errorbar(force['force_nominal_N']+(.03 if row['cycle']==2 else -.03),y,xerr=.24525,yerr=unc,fmt='o' if row['cycle']==1 else 's',color=colors[row['video']],label=f"{row['video']} cycle {row['cycle']}",capsize=3)
axes[1].set(xlabel='Assumed force [N]; ±0.245 N shared tare range',ylabel='Selected late-hold median compression [mm]')
axes[1].legend(ncol=2); axes[1].grid(alpha=.2)
fig.suptitle('Observed load comparison; no force-displacement model fitted\nVertical bars: assumed 0.3 mm + 10% sensitivity allowance, not statistical confidence intervals')
fig.tight_layout(); fig.savefig(OUT/'load_comparison.png',dpi=150); plt.close(fig)

fig,axes=plt.subplots(3,2,figsize=(12,10),sharex=False)
for ax,row in zip(axes.flat,cycles):
    d=frames[row['video']]; start=row['separation_earliest_s']; stop=row['recovery_end_s']
    subset=d[d.time_s.between(start-.4,stop)]
    ax.plot(subset.time_s-row['separation_latest_s'],subset.compression_mm,label='whole specimen')
    ax.plot(subset.time_s-row['separation_latest_s'],subset.yellow_compression_mm,label='yellow layer',alpha=.7)
    ax.axvspan(start-row['separation_latest_s'],0,color='orange',alpha=.2,label='separation bracket')
    ax.axhline(0,color='gray',lw=.7); ax.set_title(f"{row['video']} cycle {row['cycle']}: {row['free_recovery_window_s']:.2f} s free window")
    ax.set(xlabel='Time after latest separation [s]',ylabel='Residual compression [mm]'); ax.grid(alpha=.2)
axes[0,0].legend(fontsize=8)
fig.suptitle('Post-separation data: finite baseline residual is not assumed to be equilibrium')
fig.tight_layout(); fig.savefig(OUT/'free_recovery.png',dpi=150); plt.close(fig)
print(pd.DataFrame(cycles).to_string(index=False))
