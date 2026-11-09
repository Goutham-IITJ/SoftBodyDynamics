"""Reproducible, classical-CV measurements; no material/physical-model fitting.

Run from any directory: python analysis/extract.py [--video 500ml]
All generated artifacts stay under analysis/outputs. Originals are read only.
"""
import argparse
import csv
import hashlib
import json
import platform
from pathlib import Path

import cv2
import numpy as np
import scipy
from scipy.ndimage import gaussian_filter1d
from scipy.signal import find_peaks
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CFG = json.loads((HERE / "config.json").read_text())
OUT = HERE / "outputs"
SCALE = CFG["analysis_scale"]
NAN = float("nan")
cv2.setNumThreads(2)


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024*1024), b""):
            h.update(block)
    return h.hexdigest()


def write_csv(path, rows):
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def robust_line(x, y):
    x, y = np.asarray(x), np.asarray(y)
    good = np.isfinite(y)
    if good.sum() < 5:
        return NAN, NAN, NAN, good
    for _ in range(3):
        a, b = np.polyfit(x[good], y[good], 1)
        residual = y-(a*x+b)
        mad = np.median(np.abs(residual[good]-np.median(residual[good])))
        good = np.isfinite(y) & (np.abs(residual) < max(2.0, 3*1.4826*mad))
        if good.sum() < 5:
            return NAN, NAN, NAN, good
    return float(a), float(b), float(np.sqrt(np.mean(residual[good]**2))), good


def surfaces(frame, yellow_occupancy=.48, green_occupancy=.42):
    """Column occupancy, not single-pixel threshold crossings; half-resolution."""
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    yellow = ((h > 15) & (h < 43) & (s > 55) & (v > 65)).astype(np.uint8)
    green = ((h > 50) & (h < 110) & (s > 65) & (v < 155)).astype(np.uint8)
    yellow[:80] = 0
    yellow[385:] = 0
    yellow[:, :90] = 0
    yellow[:, 785:] = 0
    green[:220] = 0
    green[410:] = 0
    green[:, :90] = 0
    green[:, 785:] = 0
    xs = np.arange(155, 730, 12)
    top, interface, bottom = [], [], []
    for x in xs:
        yp = gaussian_filter1d(yellow[:, x-4:x+5].mean(axis=1), 1)
        gp = gaussian_filter1d(green[:, x-4:x+5].mean(axis=1), 1)
        yi, gi = np.flatnonzero(yp > yellow_occupancy), np.flatnonzero(gp > green_occupancy)
        top.append(float(yi[0]) if len(yi) > 20 else NAN)
        interface.append(float(yi[-1]) if len(yi) > 20 else NAN)
        bottom.append(float(gi[-1]) if len(gi) > 12 else NAN)
    top, interface, bottom = map(np.array, (top, interface, bottom))
    a, b, rms, good = robust_line(xs, top)
    # Separate card lower-edge localization: low-saturation bright strip just above foam.
    plate = []
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    for x, y in zip(xs, top):
        if not np.isfinite(y) or not np.isfinite(b):
            plate.append(NAN)
            continue
        y = int(a*x+b)
        lo, hi = max(1,y-7), y+6
        sat = np.median(s[lo:hi, x-3:x+4], axis=1)
        val = np.median(v[lo:hi, x-3:x+4], axis=1)
        smooth=gaussian_filter1d(sat.astype(float),.7)
        changes=np.diff(smooth)
        candidate=np.flatnonzero((changes>15)&(smooth[:-1]<100)&(smooth[1:]>60))
        plate.append(float(lo+candidate[np.argmax(changes[candidate])]+.5) if len(candidate) else NAN)
    plate = np.array(plate)
    pa, pb, prms, pg = robust_line(xs, plate)
    # Edge estimates are foam silhouette, separate from marker widths.
    mid = int(np.nanmedian((top+interface)/2))
    occupancy = yellow[max(0,mid-8):mid+9].mean(axis=0)
    ids = np.flatnonzero(occupancy > .5)
    left, right = (float(ids[0]), float(ids[-1])) if len(ids) else (NAN,NAN)
    return {"xs":xs, "top":top, "interface":interface, "bottom":bottom,
            "plate":plate,"plate_a":pa,"plate_b":pb,"plate_rms":prms,
            "plate_valid_fraction":float(pg.mean()),"left":left,"right":right,
            "top_a":a,"top_b":b,"top_rms":rms}


def calibrate(reference, conf, folder):
    # Detect actual 1-mm ticks, rather than assuming the marker spacing or sponge height.
    original = cv2.resize(reference, None, fx=1/SCALE, fy=1/SCALE)
    x0,y0,x1,y1 = conf["ruler_tick_roi"]
    gray = cv2.cvtColor(original, cv2.COLOR_BGR2GRAY)
    profile = 255-np.mean(gray[y0:y1,x0:x1], axis=1)
    profile = gaussian_filter1d(profile, .8)
    peaks, props = find_peaks(profile, distance=12, prominence=18)
    gaps = np.diff(peaks)
    valid = (gaps > 14) & (gaps < 24)
    if valid.sum() < 15:
        raise RuntimeError("Ruler tick detection failed; inspect manual ROI, do not invent scale")
    spacing = float(np.median(gaps[valid]))
    # Tick-index regression accommodates missing ticks; local spacing variation is diagnostic.
    tick_index = np.r_[0,np.cumsum(np.rint(gaps/spacing))]
    slope, offset = np.polyfit(tick_index, peaks+y0, 1)
    residual = peaks+y0-(slope*tick_index+offset)
    vertical_poly=np.polyfit(peaks+y0,tick_index,2)
    vertical_residual=tick_index-np.polyval(vertical_poly,peaks+y0)
    result = {"pixels_per_mm_original":float(slope), "pixels_per_mm_working":float(slope*SCALE),
              "tick_count":len(peaks), "tick_fit_rms_px":float(np.sqrt(np.mean(residual**2))),
              "local_1mm_spacing_min_px":float(np.min(gaps[valid])),
              "local_1mm_spacing_max_px":float(np.max(gaps[valid])),
              "vertical_y_to_mm_polynomial":vertical_poly.tolist(),
              "vertical_calibration_rms_mm":float(np.sqrt(np.mean(vertical_residual**2))),
              "tick_y_min_px":int(peaks[0]+y0),"tick_y_max_px":int(peaks[-1]+y0),
              "scale_systematic_fraction_assumed":CFG["scale_systematic_fraction_assumed"],
              "assumptions":"Ticks are 1 mm; ruler and observed face approximately coplanar. Quadratic y-to-mm calibration accounts for nonuniform vertical tick spacing; below the lowest tick it extrapolates. Horizontal scale is a ruler-equivalent estimate. The configured systematic sensitivity allowance is an assumption, not a calibration certificate."}
    write_csv(folder/"ruler_ticks.csv",[{"tick_index_relative":int(i),"y_original_px":int(p+y0),"fit_residual_px":float(r)} for i,p,r in zip(tick_index,peaks,residual)])
    fig,ax=plt.subplots(figsize=(8,4))
    ax.plot(np.arange(y0,y1),profile,label="ruler darkness")
    ax.plot(peaks+y0,profile[peaks],"o",label="detected 1 mm ticks")
    ax.set(xlabel="Original image y [pixel]",ylabel="Darkness",title=f"Mean scale {slope:.3f} px/mm; quadratic calibration RMS {result['vertical_calibration_rms_mm']:.3f} mm")
    ax.legend(); fig.tight_layout(); fig.savefig(folder/"calibration.png",dpi=150); plt.close(fig)
    cv2.rectangle(original,(x0,y0),(x1,y1),(0,0,255),2)
    for p in peaks: cv2.circle(original,(x0,int(p+y0)),3,(0,0,255),-1)
    cv2.imwrite(str(folder/"calibration_frame.jpg"),original)
    return result


def background_features(gray):
    mask=np.zeros_like(gray)
    mask[400:,:]=255  # tabletop, never specimen
    mask[0:390,810:]=255  # ruler labels and far-right background
    mask[0:390,:85]=255  # left background, outside bottle/specimen
    return cv2.goodFeaturesToTrack(gray,250,.005,6,mask=mask)


def registration(reference_gray, gray, reference_points):
    q,st,err=cv2.calcOpticalFlowPyrLK(reference_gray,gray,reference_points,None,winSize=(31,31),maxLevel=4)
    back,st2,_=cv2.calcOpticalFlowPyrLK(gray,reference_gray,q,None,winSize=(31,31),maxLevel=4)
    p=reference_points.reshape(-1,2); q=q.reshape(-1,2)
    fb=np.linalg.norm(back.reshape(-1,2)-p,axis=1)
    valid=(st.ravel()>0)&(st2.ravel()>0)&(fb<1.0)&(err.ravel()<25)
    if valid.sum()<8: return None, {"registration_valid":False,"background_inliers":int(valid.sum()),"registration_rms_px":NAN,"camera_dx_px":NAN,"camera_dy_px":NAN,"camera_rotation_deg":NAN,"camera_scale":NAN},p,q,valid
    matrix,inliers=cv2.estimateAffinePartial2D(p[valid],q[valid],method=cv2.RANSAC,ransacReprojThreshold=1.2,maxIters=1000)
    if matrix is None: return None,{"registration_valid":False,"background_inliers":0,"registration_rms_px":NAN,"camera_dx_px":NAN,"camera_dy_px":NAN,"camera_rotation_deg":NAN,"camera_scale":NAN},p,q,valid
    take=inliers.ravel().astype(bool)
    residual=np.linalg.norm(p[valid]@matrix[:,:2].T+matrix[:,2]-q[valid],axis=1)
    rms=float(np.sqrt(np.mean(residual[take]**2)))
    good=int(take.sum())>=8 and rms<1.0
    result={"registration_valid":good,"background_inliers":int(take.sum()),"registration_rms_px":rms/SCALE,
            "camera_dx_px":float(matrix[0,2]/SCALE),"camera_dy_px":float(matrix[1,2]/SCALE),
            "camera_rotation_deg":float(np.degrees(np.arctan2(matrix[1,0],matrix[0,0]))),
            "camera_scale":float(np.hypot(matrix[0,0],matrix[1,0]))}
    return cv2.invertAffineTransform(matrix) if good else None,result,p,q,valid


def marker_blob(frame, expected, bounds=None):
    """Dark ink centroid in a manually seeded and geometry-predicted local window.
    Missing/ambiguous detections remain NaN, never replaced by the prediction.
    """
    x,y=expected
    x0,x1=max(0,int(x)-19),min(frame.shape[1],int(x)+20)
    y0,y1=max(0,int(y)-13),min(frame.shape[0],int(y)+14)
    crop=frame[y0:y1,x0:x1]
    if crop.size==0: return NAN,NAN,0.,NAN
    hsv=cv2.cvtColor(crop,cv2.COLOR_BGR2HSV)
    gray=cv2.cvtColor(crop,cv2.COLOR_BGR2GRAY)
    # Exclude green backing and pale background; connect nearby ink fragments.
    threshold=min(135,float(np.median(gray))-22)
    mask=((gray<threshold)&((hsv[:,:,0]<55)|(hsv[:,:,1]<115))).astype(np.uint8)*255
    if bounds is not None:
        left,right,top,bottom=bounds
        yy,xx=np.indices(gray.shape)
        mask[(xx+x0<left)|(xx+x0>right)|(yy+y0<top+2)|(yy+y0>bottom+1)]=0
    mask=cv2.morphologyEx(mask,cv2.MORPH_CLOSE,np.ones((3,3),np.uint8))
    count,labels,stats,centroids=cv2.connectedComponentsWithStats(mask)
    choices=[]
    for i in range(1,count):
        area=stats[i,cv2.CC_STAT_AREA]
        if not 8<=area<=400: continue
        cx,cy=centroids[i]; distance=np.hypot(cx+x0-x,cy+y0-y)
        if distance>20: continue
        choices.append((distance-.01*area,i,cx+x0,cy+y0,area))
    if not choices: return NAN,NAN,0.,NAN
    choices.sort(); _,i,cx,cy,area=choices[0]
    pixels=labels==i
    contrast=float(np.median(gray[~pixels])-np.median(gray[pixels])) if (~pixels).any() else 0
    confidence=float(np.clip(contrast/65,0,1)*min(1,area/25))
    if len(choices)>1 and choices[1][0]-choices[0][0]<2: confidence*=.5
    if confidence<.35: return NAN,NAN,confidence,NAN
    # Sensitivity of centroid to segmentation threshold; lower bound 1 working pixel.
    centers=[]
    for trial_threshold in [threshold-10,threshold,threshold+10]:
        weights=(gray<trial_threshold)&cv2.dilate(pixels.astype(np.uint8),np.ones((3,3),np.uint8)).astype(bool)
        yy,xx=np.where(weights)
        if len(xx)>5: centers.append([xx.mean(),yy.mean()])
    uncertainty=max(1.,float(np.max(np.std(centers,axis=0)))) if centers else 2.
    return float(cx),float(cy),confidence,uncertainty


def bottle_bottom(frame,surf):
    gray=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
    hsv=cv2.cvtColor(frame,cv2.COLOR_BGR2HSV)
    values=[]
    for x in range(290,650,12):
        limit=int(surf["plate_a"]*x+surf["plate_b"])-2 if np.isfinite(surf["plate_b"]) else 100
        if limit<6: continue
        intensity=np.median(gray[:limit,x-2:x+3],axis=1)
        sat=np.median(hsv[:limit,x-2:x+3,1],axis=1)
        hit=np.flatnonzero((intensity<145)&(sat<90))
        if len(hit)>3: values.append(float(hit[-1]))
    if len(values)<10: return NAN,0.,NAN
    vals=np.array(values); med=float(np.median(vals)); mad=float(np.median(np.abs(vals-med)))
    return med,float(len(values)/30),mad


def card_left_tip(frame,surf):
    if not np.isfinite(surf['plate_b']): return NAN
    hsv=cv2.cvtColor(frame,cv2.COLOR_BGR2HSV)
    candidates=[]
    for x in range(65,150):
        y=int(surf['plate_a']*x+surf['plate_b'])
        patch=hsv[max(0,y-5):y+2,x]
        if ((patch[:,1]<75)&(patch[:,2]>155)).sum()>=2: candidates.append(x)
    for x in candidates:
        if x+1 in candidates and x+2 in candidates: return float(x)
    return NAN


def phase_at(t,conf):
    phase="card_only_baseline"; cycle=0; split="baseline"; force_state="zero"
    for c in conf["cycles"]:
        if t<c["contact"][0]: break
        cycle=c["id"]; split=c["split"]
        if t<c['contact'][1]: phase="placement_force_uncertain"; force_state="unknown"
        elif t<c["hold"][0]: phase="loaded_force_unverified"; force_state="unknown"
        elif t<=c["hold"][1]: phase="candidate_dead_weight_hold"; force_state="assumed_weight"
        elif t<c["separation"][0]: phase="transition_force_uncertain"; force_state="unknown"
        elif t<=c["separation"][1]: phase="separation_bracket"; force_state="unknown"
        else: phase="post_separation_recovery"; force_state="zero"
    return phase,cycle,split,force_state


def analyze(name,conf):
    folder=OUT/name; folder.mkdir(parents=True,exist_ok=True)
    source=ROOT/conf["path"]; hash_before=digest(source)
    cap=cv2.VideoCapture(str(source))
    metadata={"source":conf["path"],"sha256_before":hash_before,"file_bytes":source.stat().st_size,
              "width":int(cap.get(3)),"height":int(cap.get(4)),"reported_fps":cap.get(5),"reported_frames":int(cap.get(7))}
    ok,original=cap.read()
    if not ok: raise RuntimeError(f"Cannot decode {source}")
    reference=cv2.resize(original,None,fx=SCALE,fy=SCALE,interpolation=cv2.INTER_AREA)
    reference_gray=cv2.cvtColor(reference,cv2.COLOR_BGR2GRAY); points=background_features(reference_gray)
    calibration=calibrate(reference,conf,folder); ppm=calibration["pixels_per_mm_working"]
    ref=surfaces(reference)
    seeds=np.array(conf["marker_seeds"],float)*SCALE
    refmarkers=[marker_blob(reference,p,[ref['left'],ref['right'],ref['top_a']*p[0]+ref['top_b'],np.interp(p[0],ref['xs'],ref['interface'])]) for p in seeds]
    # Use measured initial centroids for prediction, retain manual seeds if undetectable.
    anchor=np.array([[m[0],m[1]] if np.isfinite(m[0]) else p for m,p in zip(refmarkers,seeds)])
    ref_top=np.nanmedian(ref["top"]); ref_int=np.nanmedian(ref["interface"])
    rows=[]; markers=[]; selected=[]; frame_index=0
    representative_times=[0,6,10,14,18,22,26,30,33]+[v for c in conf["cycles"] for key in ["contact","lifting","separation"] for v in c[key]]
    seen=set()
    # Include dense release frames in overlay sheets for manual QA.
    targets=sorted(set(representative_times+[round(c["separation"][0]+dt,3) for c in conf["cycles"] for dt in np.arange(-.2,.9,.1)]))
    while ok:
        t=cap.get(cv2.CAP_PROP_POS_MSEC)/1000
        small=cv2.resize(original,None,fx=SCALE,fy=SCALE,interpolation=cv2.INTER_AREA)
        gray=cv2.cvtColor(small,cv2.COLOR_BGR2GRAY)
        inv,reg,p,q,valid=registration(reference_gray,gray,points)
        row={"video":name,"frame":frame_index,"time_s":t,**reg}
        phase,cycle,split,state=phase_at(t,conf)
        row.update({"cycle":cycle,"split":split,"phase":phase,"force_status":state})
        masses=[(conf["water_g"]+tare)/1000 for tare in CFG["bottle_tare_g"]]
        forces=[m*CFG["gravity_m_s2"] for m in masses]
        for key,value in zip(["low","nominal","high"],forces):
            force=value if state=="assumed_weight" else (0. if state=="zero" else NAN)
            row[f"incremental_force_{key}_N"]=force
            row[f"nominal_pressure_{key}_Pa"]=force/.00365
        row["force_is_measured"]=False
        if inv is not None:
            registered=cv2.warpAffine(small,inv,(small.shape[1],small.shape[0]))
            su=surfaces(registered)
            for key in ["top","interface","bottom"]:
                row[key+"_y_px"]=float(np.nanmedian(su[key])/SCALE)
            calibrated={k:np.polyval(calibration['vertical_y_to_mm_polynomial'],su[k]/SCALE) for k in ['top','interface','bottom']}
            thickness=calibrated['bottom']-calibrated['top']
            row.update({"height_mm":float(np.nanmedian(thickness)),
                        "yellow_thickness_mm":float(np.nanmedian(calibrated['interface']-calibrated['top'])),
                        "green_thickness_mm":float(np.nanmedian(calibrated['bottom']-calibrated['interface'])),
                        "height_spatial_sd_mm":float(np.nanstd(thickness)),
                        "height_detection_valid_fraction":float(np.isfinite(thickness).mean()),
                        "left_edge_px":su["left"]/SCALE,"right_edge_px":su["right"]/SCALE,
                        "silhouette_width_mm":(su["right"]-su["left"])/ppm,
                        "plate_center_y_px":(su["plate_a"]*440+su["plate_b"])/SCALE,
                        "plate_angle_deg":float(np.degrees(np.arctan(su["plate_a"]))),
                        "plate_line_rms_mm":su["plate_rms"]/ppm,
                        "plate_left_tip_x_px":card_left_tip(registered,su)/SCALE,
                        "plate_valid_fraction":su["plate_valid_fraction"]})
            for location,indices in [("left",slice(0,12)),("center",slice(18,30)),("right",slice(-12,None))]:
                row[f"height_{location}_mm"]=float(np.nanmedian(thickness[indices]))
                row[f"plate_{location}_y_px"]=float(np.nanmedian(su["plate"][indices])/SCALE)
            # A curve residual is a diagnostic, not a measured plate stiffness.
            finite=np.isfinite(su["plate"])
            residual=su["plate"]-(su["plate_a"]*su["xs"]+su["plate_b"])
            row["plate_curve_p90_mm"]=float(np.nanpercentile(np.abs(residual),90)/ppm)
            by,bc,bmad=bottle_bottom(registered,su)
            row.update({"bottle_bottom_y_px":by/SCALE,"bottle_detection_fraction":bc,
                        "bottle_bottom_mad_mm":bmad/ppm,
                        "bottle_plate_gap_mm":(row["plate_center_y_px"]*SCALE-by)/ppm})
            top=np.nanmedian(su["top"]); interface=np.nanmedian(su["interface"])
            dx=((su["left"]+su["right"])-(ref["left"]+ref["right"]))/2
            detected=[]
            for mi,(seed,an) in enumerate(zip(seeds,anchor)):
                relative=(an[1]-ref_top)/(ref_int-ref_top)
                expected=[an[0]+dx,top+relative*(interface-top)]
                mx,my,confidence,uncertainty=marker_blob(registered,expected,[su['left'],su['right'],su['top_a']*expected[0]+su['top_b'],np.interp(expected[0],su['xs'],su['interface'])])
                record={"video":name,"frame":frame_index,"time_s":t,"marker_id":mi+1,
                        "row":["upper","middle","interface"][mi//3],"column":["left","center","right"][mi%3],
                        "x_registered_px":mx/SCALE,"y_registered_px":my/SCALE,
                        "confidence":confidence,"localization_uncertainty_mm":max(uncertainty/ppm,.4 if mi%3!=1 else .2) if np.isfinite(uncertainty) else NAN,
                        "quality_flag":"edge_marker_shape_and_clipping" if mi%3!=1 else ("interface_ink_low_contrast" if mi==7 else "interior_marker"),
                        "valid":bool(np.isfinite(mx)),"cycle":cycle,"split":split}
                markers.append(record); detected.append((mx,my,confidence))
            row["measurement_valid"]=True
            target=next((i for i,v in enumerate(targets) if i not in seen and t>=v),None)
            if target is not None:
                seen.add(target)
                overlay=registered.copy()
                for key,color in [("top",(0,255,255)),("interface",(255,100,0)),("bottom",(0,255,0)),("plate",(255,0,255))]:
                    for x,y in zip(su["xs"],su[key]):
                        if np.isfinite(y): cv2.circle(overlay,(int(x),int(y)),1,color,-1)
                for mi,(x,y,c) in enumerate(detected):
                    if np.isfinite(x):
                        cv2.circle(overlay,(round(x),round(y)),7,(0,0,255),1)
                        cv2.putText(overlay,str(mi+1),(round(x)+7,round(y)),0,.4,(0,0,255),1)
                if np.isfinite(by): cv2.line(overlay,(300,round(by)),(640,round(by)),(255,255,0),1)
                cv2.putText(overlay,f"{name} t={t:.3f}s f={frame_index} {phase}",(8,20),0,.48,(0,0,255),1)
                cv2.imwrite(str(folder/f"frame_{frame_index:05d}_overlay.jpg"),overlay)
                if abs(t-targets[target])<.2: selected.append((t,overlay))
                if targets[target] in [0,14,30,33]:
                    cv2.imwrite(str(folder/f"frame_{frame_index:05d}_original.jpg"),original)
                    diag=small.copy()
                    for a,b,g in zip(p,q,valid):
                        if g: cv2.circle(diag,tuple(np.rint(b).astype(int)),3,(0,255,0),-1)
                    cv2.imwrite(str(folder/f"frame_{frame_index:05d}_background.jpg"),diag)
        else:
            row["measurement_valid"]=False
            # Preserve rows and missing marker observations; no synthesized positions.
            for mi in range(9):
                markers.append({"video":name,"frame":frame_index,"time_s":t,"marker_id":mi+1,"row":["upper","middle","interface"][mi//3],"column":["left","center","right"][mi%3],"x_registered_px":NAN,"y_registered_px":NAN,"confidence":0.,"localization_uncertainty_mm":NAN,"quality_flag":"registration_failed","valid":False,"cycle":cycle,"split":split})
        rows.append(row)
        if frame_index%300==0: print(f"{name}: {frame_index}/{metadata['reported_frames']} t={t:.2f}",flush=True)
        ok,original=cap.read(); frame_index+=1
    cap.release()
    # Fill any failed-frame keys with explicit NaN, preserving one row per decoded frame.
    keys=list(dict.fromkeys(k for r in rows for k in r))
    rows=[{k:r.get(k,NAN) for k in keys} for r in rows]
    baseline=[r for r in rows if CFG["baseline_s"][0]<=r["time_s"]<=CFG["baseline_s"][1] and r["measurement_valid"]]
    baselines={k:float(np.nanmedian([r[k] for r in baseline])) for k in ["height_mm","yellow_thickness_mm","green_thickness_mm","plate_center_y_px","plate_angle_deg","plate_left_tip_x_px","bottom_y_px","interface_y_px","silhouette_width_mm","height_left_mm","height_center_mm","height_right_mm"]}
    baselines["height_noise_sd_mm"]=float(np.nanstd([r["height_mm"] for r in baseline]))
    # Conservative localization floor: 2 original pixels for each boundary, independent errors.
    boundary_floor=np.sqrt(2)*2/calibration["pixels_per_mm_original"]
    for r in rows:
        r["compression_mm"]=baselines["height_mm"]-r["height_mm"]
        r["yellow_compression_mm"]=baselines["yellow_thickness_mm"]-r["yellow_thickness_mm"]
        r["green_compression_mm"]=baselines["green_thickness_mm"]-r["green_thickness_mm"]
        r["plate_translation_mm"]=float(np.polyval(calibration['vertical_y_to_mm_polynomial'],r['plate_center_y_px'])-np.polyval(calibration['vertical_y_to_mm_polynomial'],baselines['plate_center_y_px']))
        r["plate_rotation_from_baseline_deg"]=r["plate_angle_deg"]-baselines["plate_angle_deg"]
        r['plate_horizontal_translation_mm']=(r['plate_left_tip_x_px']-baselines['plate_left_tip_x_px'])/calibration['pixels_per_mm_original']
        for key in ['bottom','interface']:
            r[key+'_translation_mm']=float(np.polyval(calibration['vertical_y_to_mm_polynomial'],r[key+'_y_px'])-np.polyval(calibration['vertical_y_to_mm_polynomial'],baselines[key+'_y_px']))
        r["silhouette_width_change_mm"]=r["silhouette_width_mm"]-baselines["silhouette_width_mm"]
        for loc in ["left","center","right"]: r[f"compression_{loc}_mm"]=baselines[f"height_{loc}_mm"]-r[f"height_{loc}_mm"]
        r["compression_random_uncertainty_mm"]=max(boundary_floor,2*baselines["height_noise_sd_mm"])
        r["compression_scale_systematic_mm"]=abs(r["compression_mm"])*CFG["scale_systematic_fraction_assumed"]
        r['compression_practical_resolution_assumed_mm']=.3
        r['boundary_quality_flag']='color_boundary_not_material_surface; irregular_fibres; ruler_plane_unverified'
        r['plate_quality_flag']='partially_occluded' if r['plate_valid_fraction']<.65 else 'visible_edge_fit'
    for mi in range(1,10):
        base=[m for m in markers if m["marker_id"]==mi and CFG["baseline_s"][0]<=m["time_s"]<=CFG["baseline_s"][1] and m["valid"]]
        bx=float(np.median([m["x_registered_px"] for m in base])) if base else NAN
        by=float(np.median([m["y_registered_px"] for m in base])) if base else NAN
        for m in markers:
            if m["marker_id"]==mi:
                m["dx_mm"]=(m["x_registered_px"]-bx)/calibration["pixels_per_mm_original"]
                m["dy_mm"]=float(np.polyval(calibration['vertical_y_to_mm_polynomial'],m['y_registered_px'])-np.polyval(calibration['vertical_y_to_mm_polynomial'],by))
    # Marker-pair distances remove common lateral translation; they are not Poisson ratios.
    for i,r in enumerate(rows):
        mm=markers[i*9:(i+1)*9]
        for label,first,last in [("upper",0,2),("middle",3,5),("interface",6,8)]:
            r[f"marker_{label}_width_mm"]=(mm[last]["x_registered_px"]-mm[first]["x_registered_px"])/calibration["pixels_per_mm_original"] if mm[first]["valid"] and mm[last]["valid"] else NAN
            r[f"marker_{label}_pair_confidence"]=min(mm[first]["confidence"],mm[last]["confidence"])
            r[f'marker_{label}_width_uncertainty_mm']=np.hypot(mm[first]['localization_uncertainty_mm'],mm[last]['localization_uncertainty_mm'])
    for label in ["upper","middle","interface"]:
        b=float(np.nanmedian([r[f"marker_{label}_width_mm"] for r in rows if .2<=r["time_s"]<=2]))
        for r in rows: r[f"marker_{label}_width_change_mm"]=r[f"marker_{label}_width_mm"]-b
    ts=np.array([r["time_s"] for r in rows]); dt=np.diff(ts)
    metadata.update({"decoded_frames":len(rows),"first_timestamp_s":float(ts[0]),"last_timestamp_s":float(ts[-1]),"duration_estimate_s":float(ts[-1]+np.median(dt)),"median_interval_s":float(np.median(dt)),"min_interval_s":float(dt.min()),"max_interval_s":float(dt.max()),"nonmonotonic_intervals":int((dt<=0).sum()),"intervals_over_25ms":int((dt>.025).sum()),"sha256_after":digest(source),"registration_failed_frames":sum(not r["registration_valid"] for r in rows)})
    assert metadata["sha256_before"]==metadata["sha256_after"],"Original changed during processing"
    calibration["baseline_measurements"]=baselines
    calibration["dimension_check"]={"height_measured_mm":baselines["height_mm"],"height_user_approx_mm":27,"length_measured_mm":baselines["silhouette_width_mm"],"length_user_mm":73,"yellow_measured_mm":baselines["yellow_thickness_mm"],"yellow_user_approx_mm":20,"green_measured_mm":baselines["green_thickness_mm"],"green_user_approx_mm":7}
    write_csv(folder/"measurements.csv",rows); write_csv(folder/"markers.csv",markers)
    write_csv(folder/"timestamp_gaps.csv",[{"previous_frame":int(i),"next_frame":int(i+1),"previous_time_s":float(ts[i]),"next_time_s":float(ts[i+1]),"interval_s":float(dt[i])} for i in np.flatnonzero(dt>.025)])
    (folder/"metadata.json").write_text(json.dumps(metadata,indent=2))
    (folder/"calibration.json").write_text(json.dumps(calibration,indent=2))
    phases=[]
    for c in conf["cycles"]:
        next_start=next((n["contact"][0] for n in conf["cycles"] if n["id"]>c["id"]),ts[-1])
        for key in ["contact","hold","lifting","separation"]:
            lo,hi=c[key]; phases.append({"video":name,"cycle":c["id"],"split":c["split"],"event":key,"start_s":lo,"end_s":hi,"start_frame":int(np.searchsorted(ts,lo)),"end_frame":min(len(ts)-1,int(np.searchsorted(ts,hi))),"source":"manual visual annotation; conservative bracket/window","hands_off_verified":False})
        phases.append({"video":name,"cycle":c["id"],"split":c["split"],"event":"conservative_free_recovery","start_s":c["separation"][1],"end_s":float(next_start),"start_frame":int(np.searchsorted(ts,c["separation"][1])),"end_frame":min(len(ts)-1,int(np.searchsorted(ts,next_start))),"source":"after latest separation bound until next possible contact/end","hands_off_verified":False})
    write_csv(folder/"phases.csv",phases)
    plot_video(name,rows,markers,folder)
    # Broad overview only; full-sized release overlays remain separately accessible.
    tiles=[cv2.resize(im,(480,270)) for _,im in selected[::max(1,len(selected)//20)]]
    while len(tiles)%3: tiles.append(np.zeros_like(tiles[0]))
    cv2.imwrite(str(folder/"overview_overlays.jpg"),np.vstack([np.hstack(tiles[i:i+3]) for i in range(0,len(tiles),3)]))
    print(f"{name}: done; {len(rows)} frames; scale {ppm/SCALE:.3f} px/mm",flush=True)


def plot_video(name,rows,markers,folder):
    t=np.array([r["time_s"] for r in rows])
    def series(key): return np.array([r[key] for r in rows],float)
    fig,axes=plt.subplots(4,1,figsize=(11,11),sharex=True)
    for key,label in [("compression_mm","whole specimen"),("yellow_compression_mm","yellow layer"),("green_compression_mm","green layer")]: axes[0].plot(t,series(key),label=label)
    axes[0].set_ylabel("Compression [mm]"); axes[0].legend()
    for loc in ["left","center","right"]: axes[1].plot(t,series(f"compression_{loc}_mm"),label=loc)
    axes[1].set_ylabel("Local compression [mm]"); axes[1].legend()
    axes[2].plot(t,series("plate_rotation_from_baseline_deg"),label="rotation from baseline")
    axes[2].plot(t,series("plate_curve_p90_mm"),label="90% line residual [mm]")
    axes[2].set_ylabel("Plate angle [deg] / residual"); axes[2].legend()
    axes[3].plot(t,series("incremental_force_nominal_N"),label="assumed force, gaps = unknown")
    axes[3].fill_between(t,series("incremental_force_low_N"),series("incremental_force_high_N"),alpha=.25,label="tare range")
    axes[3].set(ylabel="Incremental force [N]",xlabel="Presentation time [s]"); axes[3].legend()
    for ax in axes: ax.grid(alpha=.2)
    fig.suptitle(name+": card-only reference; no physical-parameter fit"); fig.tight_layout(); fig.savefig(folder/"trajectories.png",dpi=150); plt.close(fig)
    fig,axes=plt.subplots(3,1,figsize=(11,8),sharex=True)
    for key in ["camera_dx_px","camera_dy_px"]: axes[0].plot(t,series(key),label=key)
    axes[0].set_ylabel("Image transform [pixel]"); axes[0].legend()
    axes[1].plot(t,series("camera_rotation_deg"),label="rotation [deg]"); axes[1].plot(t,(series("camera_scale")-1)*100,label="scale change [%]"); axes[1].legend()
    axes[2].plot(t,series("registration_rms_px"),label="inlier RMS [original pixel]"); axes[2].legend(); axes[2].set_xlabel("Presentation time [s]")
    fig.suptitle(name+": background registration diagnostics"); fig.tight_layout(); fig.savefig(folder/"registration.png",dpi=150); plt.close(fig)
    fig,axes=plt.subplots(2,1,figsize=(11,7),sharex=True)
    for label in ["upper","middle","interface"]: axes[0].plot(t,series(f"marker_{label}_width_change_mm"),label=label)
    axes[0].plot(t,series("silhouette_width_change_mm"),label="silhouette",alpha=.5)
    axes[0].set_ylabel("Width change [mm]"); axes[0].legend()
    for mi in [4,5,6]:
        m=[v for v in markers if v["marker_id"]==mi]
        axes[1].plot([v["time_s"] for v in m],[v["dx_mm"] for v in m],label=f"marker {mi}")
    axes[1].set(ylabel="Registered lateral displacement [mm]",xlabel="Presentation time [s]"); axes[1].legend()
    fig.suptitle(name+": lateral measurements (missing detections remain gaps)"); fig.tight_layout(); fig.savefig(folder/"lateral.png",dpi=150); plt.close(fig)


if __name__=="__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("--video",choices=list(CFG["videos"])); args=parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"environment.json").write_text(json.dumps({"python":platform.python_version(),"opencv":cv2.__version__,"numpy":np.__version__,"scipy":scipy.__version__,"matplotlib":matplotlib.__version__,"config_sha256":digest(HERE/"config.json"),"script_sha256":digest(Path(__file__))},indent=2))
    (OUT/'config_used.json').write_text(json.dumps(CFG,indent=2))
    for name,conf in CFG["videos"].items():
        if args.video is None or args.video==name: analyze(name,conf)
