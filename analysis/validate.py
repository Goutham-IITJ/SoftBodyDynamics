"""Integrity, timing, missing-data, registration and segmentation sensitivity checks.
These verify measurement plumbing; they do not validate a physical model.
"""
import json
from pathlib import Path
import cv2
import numpy as np
import pandas as pd
from extract import CFG, ROOT, OUT, SCALE, digest, surfaces, registration, background_features

checks=[]
sensitivity=[]
for name,conf in CFG['videos'].items():
    folder=OUT/name
    d=pd.read_csv(folder/'measurements.csv')
    m=pd.read_csv(folder/'markers.csv')
    meta=json.loads((folder/'metadata.json').read_text())
    cal=json.loads((folder/'calibration.json').read_text())
    assert len(d)==meta['decoded_frames']==meta['reported_frames']
    assert len(m)==9*len(d)
    assert np.allclose(m.time_s.to_numpy(),np.repeat(d.time_s.to_numpy(),9),atol=1e-9)
    assert np.array_equal(m.frame.to_numpy(),np.repeat(d.frame.to_numpy(),9))
    assert (np.diff(d.time_s)>0).all()
    assert np.array_equal(d.frame,np.arange(len(d)))
    assert meta['sha256_before']==meta['sha256_after']==digest(ROOT/conf['path'])
    unknown=d.force_status=='unknown'
    assert d.loc[unknown,'incremental_force_nominal_N'].isna().all()
    assert (d.loc[d.force_status=='zero','incremental_force_nominal_N']==0).all()
    assert np.allclose(d.loc[d.force_status=='assumed_weight','incremental_force_nominal_N'],(conf['water_g']+75)/1000*9.81)
    assert m.loc[~m.valid,['x_registered_px','y_registered_px']].isna().all().all()
    assert (d.height_mm>0).all() and (d.yellow_thickness_mm>0).all() and (d.green_thickness_mm>0).all()
    for c in conf['cycles']:
        assert (d.loc[d.cycle==c['id'],'split']==c['split']).all()
    p=cal['vertical_y_to_mm_polynomial']
    assert (np.polyval(np.polyder(p),np.arange(0,850))>0).all()
    checks.append({'video':name,'integrity_timing_force_split_checks':'PASS','frames':len(d),'source_sha256':meta['sha256_after']})
    cap=cv2.VideoCapture(str(ROOT/conf['path']),cv2.CAP_FFMPEG,[cv2.CAP_PROP_N_THREADS,2])
    ok,ref=cap.read(); assert ok
    ref=cv2.resize(ref,None,fx=SCALE,fy=SCALE,interpolation=cv2.INTER_AREA)
    rg=cv2.cvtColor(ref,cv2.COLOR_BGR2GRAY); points=background_features(rg)
    # Known synthetic camera transform of a real image: material shape is unchanged.
    warp=cv2.getRotationMatrix2D((480,270),.7,1.01); warp[:,2]+=[6,-4]
    moved=cv2.warpAffine(ref,warp,(960,540))
    inverse,reg,_,_,_=registration(rg,cv2.cvtColor(moved,cv2.COLOR_BGR2GRAY),points)
    assert inverse is not None
    sample=np.array([[150.,120.],[440.,230.],[720.,370.]])
    recovered=(sample@warp[:,:2].T+warp[:,2])@inverse[:,:2].T+inverse[:,2]
    error=float(np.max(np.linalg.norm(recovered-sample,axis=1))/SCALE)
    assert error<2.0, f'{name} synthetic registration error {error}'
    checks[-1]['synthetic_camera_max_error_original_px']=error
    requested=[t for t in [0,6,10,14,18,22,26,30,33] if t<=d.time_s.iloc[-1]]
    # Decode sequentially: random seek frame counters are unreliable for these VFR clips.
    cap.release(); cap=cv2.VideoCapture(str(ROOT/conf['path']),cv2.CAP_FFMPEG,[cv2.CAP_PROP_N_THREADS,2])
    idx=0; ri=0; ok,f=cap.read()
    samples=[]
    while ok:
        pts=cap.get(cv2.CAP_PROP_POS_MSEC)/1000
        assert idx<len(d) and abs(pts-d.time_s.iloc[idx])<1e-9, (name,idx,pts)
        if ri<len(requested) and pts>=requested[ri]: samples.append((idx,pts,f.copy())); ri+=1
        idx+=1; ok,f=cap.read()
    assert idx==len(d)
    checks[-1]['all_sequential_frame_timestamps']='PASS'
    checks[-1]['marker_frame_timestamp_join']='PASS'
    for image_path in folder.glob('frame_*.jpg'):
        image_index=int(image_path.name.split('_')[1])
        assert 0<=image_index<len(d)
    for idx,pts,f in samples:
        f=cv2.resize(f,None,fx=SCALE,fy=SCALE,interpolation=cv2.INTER_AREA)
        inv,reg,_,_,_=registration(rg,cv2.cvtColor(f,cv2.COLOR_BGR2GRAY),points)
        if inv is None: continue
        f=cv2.warpAffine(f,inv,(960,540))
        heights=[]; yellow=[]; green=[]
        for yt,gt in [(.35,.30),(.48,.42),(.60,.55)]:
            su=surfaces(f,yt,gt)
            t=np.polyval(p,su['top']/SCALE); inter=np.polyval(p,su['interface']/SCALE); b=np.polyval(p,su['bottom']/SCALE)
            heights.append(float(np.nanmedian(b-t))); yellow.append(float(np.nanmedian(inter-t))); green.append(float(np.nanmedian(b-inter)))
        assert abs(pts-d.time_s.iloc[idx])<1e-6
        sensitivity.append({'video':name,'frame':idx,'time_s':pts,'height_threshold_range_mm':np.ptp(heights),'yellow_threshold_range_mm':np.ptp(yellow),'green_threshold_range_mm':np.ptp(green)})
    cap.release()
pd.DataFrame(checks).to_csv(OUT/'validation_checks.csv',index=False)
pd.DataFrame(sensitivity).to_csv(OUT/'segmentation_sensitivity.csv',index=False)
print(pd.DataFrame(checks).to_string(index=False))
print(pd.DataFrame(sensitivity).groupby('video').max().to_string())
