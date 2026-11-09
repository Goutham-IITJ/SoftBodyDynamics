"""Phase 7A image observations only. No force inversion, fitting, or FEM changes."""
from pathlib import Path
import csv,json,sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from inspect_videos import ROOT,OUT,sha,write_csv
import cv2
import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.signal import find_peaks
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

CONFIG={
 'half_area':dict(source='Videos/half area.mp4',roi=[300,130,1395,670],ruler=[1418,10,1442,605],reference=[.2,1.2],
                  selected=[0,55,65,80,95,125,155,185,200,210,225,245,270,300,330,360,380,390,400,425,451],
                  windows=[('cycle1_late_hold',4.2,6.2),('between_cycles',7.5,8.3),('cycle2_late_hold',10.0,12.3),('final_recovery',14.,15.)]),
 'fingertip':dict(source='Videos/fingertip.mp4',roi=[350,0,1438,530],ruler=[1450,0,1472,465],reference=[.2,1.2],
                  selected=[0,48,55,70,100,130,150,164,170,178,195,207,225,245,265,280,290,300,309,335,365,390,400,410,430,440],
                  windows=[('central_deep',3.8,5.0),('central_recovery',6.,6.5),('left_deep',7.8,8.8),('left_recovery',9.7,10.),('right_deep',11.5,12.6),('final_recovery',14.,14.6)])}
U=np.linspace(.05,.95,19)


def save_configuration():
    import hashlib
    here=Path(__file__).resolve().parent
    paths=[here/n for n in ['inspect_videos.py','analyze.py','refine_sheets.py','summarize.py','test_analysis.py']]
    (OUT/'analysis_configuration.json').write_text(json.dumps(dict(experiments=CONFIG,profile_u=U.tolist(),
      coordinate_system='Original 1920x1080 px; registered to first-frame ruler/background, y positive down; median reference 0.2-1.2s',
      processing_scale=.5,top_boundary='visible yellow color envelope; not reconstructed hidden top',force_inversion=False,
      code_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}),indent=2)+'\n')


def largest(mask):
    n,labels,stats,_=cv2.connectedComponentsWithStats(mask.astype(np.uint8))
    if n<2:return np.zeros_like(mask,bool)
    index=1+np.argmax(stats[1:,cv2.CC_STAT_AREA]);return labels==index


def foam_components(mask):
    # A finger can split the projected yellow region into two disconnected lobes.
    # Retain both measured regions; never bridge the hidden top or drop a lobe.
    n,labels,stats,_=cv2.connectedComponentsWithStats(mask.astype(np.uint8))
    keep=np.flatnonzero(stats[:,cv2.CC_STAT_AREA]>=1000);keep=keep[keep!=0]
    return np.isin(labels,keep)


def median(value):
    value=np.asarray(value,float)
    return float(np.nanmedian(value)) if np.isfinite(value).any() else np.nan


def calibration(reference,roi,folder):
    x0,y0,x1,y1=roi;gray=cv2.cvtColor(reference,cv2.COLOR_BGR2GRAY)
    darkness=gaussian_filter1d(255-gray[y0:y1,x0:x1].mean(axis=1),.8)
    peaks,_=find_peaks(darkness,distance=9,prominence=12)
    gaps=np.diff(peaks);spacing=float(np.median(gaps))
    assert 10<spacing<20 and len(peaks)>=20,(peaks,spacing)
    tick=np.r_[0,np.cumsum(np.rint(gaps/spacing))];ys=peaks+y0
    poly=np.polyfit(ys,tick,2);error=np.polyval(poly,ys)-tick
    assert max(abs(error))<.15 and np.all(np.diff(ys)>0),(ys,error)
    result=dict(ruler_roi_original_px=roi,assumed_minor_tick_mm=1,detected_ticks=len(ys),
                median_px_per_mm=spacing,minimum_tick_gap_px=float(gaps.min()),maximum_tick_gap_px=float(gaps.max()),
                y_to_relative_mm_polynomial=poly.tolist(),fit_RMS_mm=float(np.sqrt(np.mean(error**2))),
                tick_y_min_px=int(ys.min()),tick_y_max_px=int(ys.max()),
                caution='Ruler-equivalent vertical metric only; face/ruler coplanarity and lens perspective unverified. Horizontal distances use mean vertical scale, not a calibrated planar homography.')
    write_csv(folder/'ruler_ticks.csv',(dict(relative_tick_mm=float(t),y_px=int(y),fit_residual_mm=float(e)) for t,y,e in zip(tick,ys,error)))
    (folder/'calibration.json').write_text(json.dumps(result,indent=2)+'\n')
    fig,ax=plt.subplots(figsize=(9,3.5));ax.plot(np.arange(y0,y1),darkness);ax.plot(ys,darkness[peaks],'o',ms=4)
    ax.set(xlabel='Original image y (px)',ylabel='Ruler darkness',title=f'{len(ys)} minor ticks; {spacing:.2f} px/mm; polynomial RMS {result["fit_RMS_mm"]:.4f} mm (tick fit only)')
    fig.tight_layout();fig.savefig(folder/'calibration.png',dpi=150);plt.close(fig)
    image=reference.copy();cv2.rectangle(image,(x0,y0),(x1,y1),(0,0,255),2)
    for y in ys:cv2.circle(image,(x0,int(y)),4,(0,0,255),-1)
    cv2.imwrite(str(folder/'calibration_evidence.jpg'),image)
    return result


def background(reference):
    gray=cv2.cvtColor(cv2.resize(reference,(960,540)),cv2.COLOR_BGR2GRAY)
    mask=np.zeros_like(gray);mask[:325,735:830]=255;mask[20:350,870:955]=255
    points=cv2.goodFeaturesToTrack(gray,200,.005,5,mask=mask)
    assert points is not None and len(points)>=12
    return gray,points


def register(frame,reference_gray,points):
    gray=cv2.cvtColor(cv2.resize(frame,(960,540)),cv2.COLOR_BGR2GRAY)
    q,st,error=cv2.calcOpticalFlowPyrLK(reference_gray,gray,points,None,winSize=(25,25),maxLevel=3)
    back,st2,_=cv2.calcOpticalFlowPyrLK(gray,reference_gray,q,None,winSize=(25,25),maxLevel=3)
    p=points.reshape(-1,2);qq=q.reshape(-1,2)
    good=(st.ravel()>0)&(st2.ravel()>0)&(error.ravel()<25)&(np.linalg.norm(back.reshape(-1,2)-p,axis=1)<.75)
    if good.sum()<8:return None,dict(valid=False,inliers=int(good.sum()),rms_px=np.nan,dx_px=np.nan,dy_px=np.nan,scale=np.nan,angle_deg=np.nan)
    M,inliers=cv2.estimateAffinePartial2D(p[good],qq[good],method=cv2.RANSAC,ransacReprojThreshold=1.,maxIters=1000)
    if M is None:return None,dict(valid=False,inliers=0,rms_px=np.nan,dx_px=np.nan,dy_px=np.nan,scale=np.nan,angle_deg=np.nan)
    take=inliers.ravel().astype(bool);res=np.linalg.norm(p[good]@M[:,:2].T+M[:,2]-qq[good],axis=1)*2
    rms=float(np.sqrt(np.mean(res[take]**2)));valid=take.sum()>=8 and rms<1.5
    inverse=cv2.invertAffineTransform(M);inverse[:,2]*=2
    info=dict(valid=bool(valid),inliers=int(take.sum()),rms_px=rms,dx_px=float(M[0,2]*2),dy_px=float(M[1,2]*2),
              scale=float(np.hypot(M[0,0],M[1,0])),angle_deg=float(np.degrees(np.arctan2(M[1,0],M[0,0]))))
    return cv2.warpAffine(frame,inverse,(1920,1080)) if valid else None,info


def masks(frame,roi):
    small=cv2.resize(frame,(960,540));h,s,v=cv2.split(cv2.cvtColor(small,cv2.COLOR_BGR2HSV));x0,y0,x1,y1=(np.array(roi)//2).astype(int)
    allowed=np.zeros_like(h,bool);allowed[y0:y1,x0:x1]=True
    yellow=foam_components((h>=18)&(h<44)&(s>55)&(v>65)&allowed)
    green=largest((h>=42)&(h<112)&(s>60)&(v<170)&allowed)
    return yellow,green,(h,s,v),allowed


def profile(yellow,green,xs,threshold=.45):
    top=[];interface=[];bottom=[];green_top=[]
    for x in xs:
        xx=round(x/2);yp=gaussian_filter1d(yellow[:,xx-3:xx+4].mean(axis=1),1.)
        gp=gaussian_filter1d(green[:,xx-3:xx+4].mean(axis=1),1.)
        yi=np.flatnonzero(yp>threshold);gi=np.flatnonzero(gp>threshold)
        top.append(float(yi[0]*2) if len(yi)>10 else np.nan);interface.append(float(yi[-1]*2) if len(yi)>10 else np.nan)
        green_top.append(float(gi[0]*2) if len(gi)>10 else np.nan);bottom.append(float(gi[-1]*2) if len(gi)>10 else np.nan)
    return np.array([top,interface,green_top,bottom])


def finger(hsv,allowed):
    h,s,v=hsv;mask=((h<18)&(s>45)&(v>30)&allowed).astype(np.uint8)
    mask=cv2.morphologyEx(mask,cv2.MORPH_OPEN,np.ones((3,3),np.uint8))
    n,labels,stats,_=cv2.connectedComponentsWithStats(mask)
    choices=[i for i in range(1,n) if stats[i,cv2.CC_STAT_TOP]<4 and stats[i,cv2.CC_STAT_HEIGHT]>25 and stats[i,cv2.CC_STAT_AREA]>300]
    if not choices:return dict(tip_x=np.nan,tip_y=np.nan,low_left=np.nan,low_right=np.nan,occlusion_left=np.nan,occlusion_right=np.nan,visible=False)
    i=max(choices,key=lambda k:stats[k,cv2.CC_STAT_AREA]);yy,xx=np.where(labels==i);tip=int(np.max(yy));near=yy>=tip-2
    lower=(yy>=tip-30)&(yy<=tip-7)
    return dict(tip_x=float(np.median(xx[near])*2),tip_y=float(tip*2),low_left=float(xx[lower].min()*2),low_right=float(xx[lower].max()*2),occlusion_left=float(xx.min()*2),occlusion_right=float(xx.max()*2),visible=True)


def run():
    save_configuration();cv2.setNumThreads(2);provenance=json.loads((OUT/'baseline_provenance.json').read_text())
    all_summary=[]
    for slug,conf in CONFIG.items():
        folder=OUT/slug;cap=cv2.VideoCapture(str(ROOT/conf['source']),cv2.CAP_FFMPEG,[cv2.CAP_PROP_N_THREADS,2])
        ok,reference=cap.read();assert ok
        cal=calibration(reference,conf['ruler'],folder);poly=np.array(cal['y_to_relative_mm_polynomial']);refgray,points=background(reference)
        yy,gg,_,_=masks(reference,conf['roi']);ys,xs0=np.where(yy);left,right=np.quantile(xs0,[.002,.998])*2
        xs=left+U*(right-left);records=[];selected={};i=0;frame=reference
        while ok:
            t=cap.get(cv2.CAP_PROP_POS_MSEC)/1000;aligned,reg=register(frame,refgray,points)
            row=dict(frame=i,time_s=t,**{'registration_'+k:v for k,v in reg.items()})
            if aligned is None:
                p=np.full((4,len(U)),np.nan);tip=dict(tip_x=np.nan,tip_y=np.nan,low_left=np.nan,low_right=np.nan,occlusion_left=np.nan,occlusion_right=np.nan,visible=False);edges=[np.nan,np.nan];sensitivity=np.nan;range_mm=np.full(len(U),np.nan)
            else:
                yellow,green,hsv,allowed=masks(aligned,conf['roi']);p=profile(yellow,green,xs)
                tip=finger(hsv,allowed) if slug=='fingertip' else dict(tip_x=np.nan,tip_y=np.nan,low_left=np.nan,low_right=np.nan,occlusion_left=np.nan,occlusion_right=np.nan,visible=False)
                _,xedge=np.where(yellow);edges=np.quantile(xedge,[.002,.998])*2 if len(xedge) else [np.nan,np.nan]
                low=profile(yellow,green,xs,.35);high=profile(yellow,green,xs,.55)
                sensitivity=float(np.nanmax(np.abs(low-high)))
                range_mm=np.abs((np.polyval(poly,low[3])-np.polyval(poly,low[0]))-(np.polyval(poly,high[3])-np.polyval(poly,high[0])))
            row.update(tip);row.update(face_left_px=float(edges[0]),face_right_px=float(edges[1]),threshold_sensitivity_max_px=sensitivity)
            records.append((row,p,range_mm))
            if i in conf['selected']:selected[i]=(frame.copy(),aligned.copy() if aligned is not None else frame.copy())
            i+=1;ok,frame=cap.read()
        cap.release()
        baseline=np.nanmedian(np.stack([p for row,p,_ in records if conf['reference'][0]<=row['time_s']<=conf['reference'][1]]),axis=0)
        assert np.isfinite(baseline).all()
        sample_rows=[];profile_rows=[];baserows=[]
        for u,x,p0 in zip(U,xs,baseline.T):baserows.append(dict(u_reference=u,x_px=x,top_y_px=p0[0],yellow_bottom_y_px=p0[1],green_top_y_px=p0[2],bottom_y_px=p0[3],total_height_mm=np.polyval(poly,p0[3])-np.polyval(poly,p0[0])))
        write_csv(folder/'reference_profile.csv',baserows)
        for row,p,range_mm in records:
            top_delta=p[0]-baseline[0];bottom_delta=p[3]-baseline[3]
            compression_px=top_delta-bottom_delta
            height=np.polyval(poly,p[3])-np.polyval(poly,p[0]);height0=np.polyval(poly,baseline[3])-np.polyval(poly,baseline[0]);comp_mm=height0-height
            backing=(np.polyval(poly,baseline[3])-np.polyval(poly,baseline[2]))-(np.polyval(poly,p[3])-np.polyval(poly,p[2]))
            occluded=np.array([row['visible'] and row['occlusion_left']-8<=x<=row['occlusion_right']+8 for x in xs])
            row['median_backing_bottom_shift_px']=median(bottom_delta);row['median_green_thickness_change_mm']=median(backing)
            row['median_backing_bottom_shift_mm']=median(np.polyval(poly,p[3])-np.polyval(poly,baseline[3]))
            row['left_region_compression_mm']=median(comp_mm[(U>=.1-1e-8)&(U<=.3+1e-8)])
            row['center_region_compression_mm']=median(comp_mm[(U>=.4-1e-8)&(U<=.6+1e-8)])
            row['right_region_compression_mm']=median(comp_mm[(U>=.7-1e-8)&(U<=.9+1e-8)])
            row['tip_apparent_depth_px']=np.nan;row['tip_apparent_depth_mm']=np.nan;row['tip_u_reference']=np.nan
            if row['visible']:
                row['tip_u_reference']=(row['tip_x']-left)/(right-left)
                t0=np.interp(row['tip_x'],xs,baseline[0]);b0=np.interp(row['tip_x'],xs,baseline[3]);bb=np.interp(row['tip_x'],xs,p[3])
                row['tip_apparent_depth_px']=row['tip_y']-t0-(bb-b0)
                row['tip_apparent_depth_mm']=(np.polyval(poly,row['tip_y'])-np.polyval(poly,t0))-(np.polyval(poly,bb)-np.polyval(poly,b0))
            for j,(u,x) in enumerate(zip(U,xs)):
                profile_rows.append(dict(frame=row['frame'],time_s=row['time_s'],u_reference=u,x_reference_px=x,registration_valid=row['registration_valid'],
                  top_visible_color_y_px=p[0,j],yellow_bottom_y_px=p[1,j],green_top_y_px=p[2,j],bottom_y_px=p[3,j],
                  top_shift_px=top_delta[j],bottom_shift_px=bottom_delta[j],visible_thickness_compression_px=compression_px[j],
                  visible_thickness_compression_mm=comp_mm[j],green_thickness_compression_mm=backing[j],
                  fingertip_occludes_true_top=bool(occluded[j]),threshold_height_range_mm=range_mm[j],
                  edge_dominated_sample=bool(u<.1-1e-8 or u>.9+1e-8),
                  practical_localization_allowance_mm=max(.3,range_mm[j]/2) if np.isfinite(range_mm[j]) else np.nan,
                  separate_assumed_scale_allowance_mm=.1*abs(comp_mm[j]),metric_is_ruler_equivalent=True))
            sample_rows.append(row)
        write_csv(folder/'measurements.csv',sample_rows);write_csv(folder/'profiles.csv',profile_rows)
        for label,a,b in conf['windows']:
            subset=[r for r in sample_rows if a<=r['time_s']<=b];assert subset
            item=dict(experiment=slug,window=label,start_s=a,end_s=b,first_frame=subset[0]['frame'],last_frame=subset[-1]['frame'],samples=len(subset))
            for k in ['left_region_compression_mm','center_region_compression_mm','right_region_compression_mm','median_green_thickness_change_mm','median_backing_bottom_shift_px','median_backing_bottom_shift_mm','tip_apparent_depth_mm','tip_u_reference']:
                v=np.array([r[k] for r in subset]);item[k]=float(np.nanmedian(v)) if np.isfinite(v).any() else np.nan
            all_summary.append(item)
        selected_rows=[];events=[]
        for index,(raw,aligned) in selected.items():
            row,p,_=records[index];annotated=aligned.copy()
            for j,x in enumerate(xs):
                for y,color in zip(p[:,j],[(0,220,255),(255,180,0),(255,0,0),(0,180,0)]):
                    if np.isfinite(y):cv2.circle(annotated,(round(x),round(y)),4,color,-1)
            if row['visible']:
                cv2.circle(annotated,(round(row['tip_x']),round(row['tip_y'])),9,(0,0,255),2)
                cv2.putText(annotated,'Red: visible finger tip proxy; true top occluded',(30,1000),0,.7,(0,0,255),2)
            cv2.putText(annotated,f'{slug}: frame {index}, PTS {row["time_s"]:.3f}s; ruler-registered',(30,40),0,.8,(0,0,255),2)
            cv2.imwrite(str(folder/f'selected_{index:05d}_original.jpg'),raw,[cv2.IMWRITE_JPEG_QUALITY,96]);cv2.imwrite(str(folder/f'selected_{index:05d}_annotated.jpg'),annotated,[cv2.IMWRITE_JPEG_QUALITY,96])
            selected_rows.append(dict(frame=index,time_s=row['time_s'],original=f'selected_{index:05d}_original.jpg',annotated=f'selected_{index:05d}_annotated.jpg'))
            tile=cv2.resize(annotated,(640,360));events.append(tile)
        while len(events)%4:events.append(np.full_like(events[0],255))
        cv2.imwrite(str(folder/'selected_contact_sheet.jpg'),np.vstack([np.hstack(events[k:k+4]) for k in range(0,len(events),4)]))
        write_csv(folder/'selected_manifest.csv',selected_rows)
        plot(slug,folder,sample_rows,profile_rows,conf)
        print(slug,'frames',len(records),'reference edges',left,right,'calibration',cal,flush=True)
    write_csv(OUT/'window_summary.csv',all_summary)
    assert all(sha(ROOT/p)==h for p,h in provenance['protected_sha256'].items())
    (OUT/'preservation_check.json').write_text(json.dumps(dict(status='PASS',protected_files_unchanged=len(provenance['protected_sha256']),no_material_fit=True,no_new_physics=True),indent=2)+'\n')


def plot(slug,folder,rows,profiles,conf):
    fig,axes=plt.subplots(2,1,figsize=(11,7),sharex=True);t=[r['time_s'] for r in rows]
    for region in ['left','center','right']:axes[0].plot(t,[r[f'{region}_region_compression_mm'] for r in rows],label=f'{region} region')
    if slug=='fingertip':axes[0].plot(t,[r['tip_apparent_depth_mm'] for r in rows],color='black',ls=':',label='Visible tip proxy (not true hidden surface)')
    axes[0].set(ylabel='Apparent compression (ruler-equivalent mm)');axes[0].legend(fontsize=8)
    axes[1].plot(t,[r['median_green_thickness_change_mm'] for r in rows],label='Green visible thickness decrease (mm)')
    axes[1].plot(t,[r['median_backing_bottom_shift_mm'] for r in rows],label='Visible bottom motion in ruler frame (mm)')
    axes[1].set(xlabel='Decoded presentation timestamp (s)',ylabel='Ruler-frame displacement');axes[1].legend(fontsize=8)
    for ax in axes:ax.grid(alpha=.25);ax.axhline(0,color='gray',lw=.6)
    fig.suptitle(f'{slug}: image observations only; unknown force during transitions / all finger presses')
    fig.tight_layout();fig.savefig(folder/'temporal_observations.png',dpi=160);plt.close(fig)
    fig,ax=plt.subplots(figsize=(10,5))
    for label,a,b in conf['windows']:
        xx=[r for r in profiles if a<=r['time_s']<=b]
        values=[median([r['visible_thickness_compression_mm'] for r in xx if abs(r['u_reference']-u)<1e-8 and not r['fingertip_occludes_true_top']]) for u in U]
        values=[v if .1-1e-8<=u<=.9+1e-8 else np.nan for u,v in zip(U,values)]
        ax.plot(U,values,'o-',ms=3,label=label)
    ax.axhline(0,color='gray',lw=.6);ax.set(xlabel='Reference image face fraction u (not tracked material coordinate)',ylabel='Visible thickness compression (ruler-equivalent mm)',title='Occluded points and edge-dominated 5% bins omitted; no hidden-surface reconstruction')
    ax.legend(fontsize=8);ax.grid(alpha=.2);fig.tight_layout();fig.savefig(folder/'deformation_profiles.png',dpi=160);plt.close(fig)


if __name__=='__main__':run()
