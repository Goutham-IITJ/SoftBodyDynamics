"""Reapply reviewed phase annotations without rerunning image extraction.
Useful for a semi-automated workflow: edit config.json, run this, then summarize.
Geometry CSV values are retained exactly as parsed, without refitting or interpolation.
"""
import json
import cv2
import numpy as np
import pandas as pd
from extract import CFG, HERE, OUT, digest, phase_at, plot_video

for name,conf in CFG['videos'].items():
    folder=OUT/name
    d=pd.read_csv(folder/'measurements.csv'); m=pd.read_csv(folder/'markers.csv')
    d['plate_translation_uncertainty_assumed_mm']=np.maximum(.2,d.plate_line_rms_mm)
    d['plate_angle_uncertainty_assumed_deg']=np.maximum(.1,np.degrees(np.arctan(d.plate_line_rms_mm/30)))
    d['bottle_bottom_uncertainty_assumed_mm']=np.maximum(.2,d.bottle_bottom_mad_mm)
    d.loc[d.bottle_bottom_y_px.isna(),'bottle_bottom_uncertainty_assumed_mm']=np.nan
    for layer in ['yellow','green']:
        d[layer+'_compression_uncertainty_assumed_mm']=.3+CFG['scale_systematic_fraction_assumed']*d[layer+'_compression_mm'].abs()
    for index,r in d.iterrows():
        phase,cycle,split,state=phase_at(r.time_s,conf)
        d.loc[index,['phase','cycle','split','force_status']]=[phase,cycle,split,state]
        for label,tare in zip(['low','nominal','high'],CFG['bottle_tare_g']):
            force=(conf['water_g']+tare)/1000*9.81 if state=='assumed_weight' else (0. if state=='zero' else np.nan)
            d.loc[index,f'incremental_force_{label}_N']=force
            d.loc[index,f'nominal_pressure_{label}_Pa']=force/.00365
    m['cycle']=m.frame.map(d.set_index('frame').cycle)
    m['split']=m.frame.map(d.set_index('frame').split)
    d.to_csv(folder/'measurements.csv',index=False); m.to_csv(folder/'markers.csv',index=False)
    records=[]
    for c in conf['cycles']:
        end=next((n['contact'][0] for n in conf['cycles'] if n['id']>c['id']),d.time_s.iloc[-1])
        for event,interval in [(k,c[k]) for k in ['contact','hold','lifting','separation']]+[('conservative_free_recovery',[c['separation'][1],end])]:
            records.append({'video':name,'cycle':c['id'],'split':c['split'],'event':event,'start_s':interval[0],'end_s':interval[1],
                            'start_frame':int(np.searchsorted(d.time_s,interval[0])),
                            'end_frame':min(len(d)-1,int(np.searchsorted(d.time_s,interval[1]))),
                            'source':'manual visual annotation; conservative bracket/window','hands_off_verified':False})
    pd.DataFrame(records).to_csv(folder/'phases.csv',index=False)
    # Keep existing overlay image measurements, update their phase labels only.
    for path in folder.glob('frame_*_overlay.jpg'):
        idx=int(path.name.split('_')[1]); r=d.iloc[idx]
        im=cv2.imread(str(path)); im[:25,:]=230
        cv2.putText(im,f'{name} t={r.time_s:.3f}s f={idx} {r.phase}',(8,20),0,.48,(0,0,255),1)
        cv2.imwrite(str(path),im)
    plot_video(name,d.to_dict('records'),m.to_dict('records'),folder)
(OUT/'annotation_provenance.json').write_text(json.dumps({'config_sha256':digest(HERE/'config.json'),'script_sha256':digest(HERE/'annotate.py'),'method':'Manual event brackets and conservative candidate hold windows; no direct hand-force observation.'},indent=2))
(OUT/'config_used.json').write_text(json.dumps(CFG,indent=2))
