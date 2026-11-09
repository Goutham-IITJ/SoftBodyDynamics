"""Reviewed events and descriptive image summaries, not a constitutive inverse fit."""
from inspect_videos import ROOT,OUT,write_csv,sha
from analyze import CONFIG,U,median,background,register
import json
import numpy as np
import pandas as pd
import cv2

# Conservative presentation-time brackets reviewed on dense sequential contact sheets.
EVENTS={
 'half_area':[
  ('reference',.2,1.2,'Card present; bottle not supporting its full weight'),
  ('cycle1_possible_bottle_card_contact',1.6,1.9,'Contact appearance only; transmitted force unknown'),
  ('cycle1_visible_load_onset',2.4,2.7,'Foam depression becomes clear; not a known force step'),
  ('cycle1_candidate_late_hold',4.2,6.2,'No hand visible in crop; top of bottle outside view, hands-off not certified'),
  ('cycle1_unloading_onset',6.4,6.6,'Lift/recovery begins; unknown transmitted force'),
  ('cycle1_bottle_separation',7.0,7.2,'Clear bottle-card gap by conservative later bound; card stays on foam'),
  ('cycle1_card_only_recovery',7.2,8.8,'No bottle contact before conservative next-contact bound'),
  ('cycle2_possible_bottle_card_contact',8.8,9.0,'Appearance bracket, not measured force'),
  ('cycle2_visible_load_onset',9.1,9.3,'Nonuniform depression increases'),
  ('cycle2_candidate_late_hold',10.,12.3,'Residual motion present; neither force nor hands-off status measured'),
  ('cycle2_unloading_onset',12.6,12.8,'Unknown transmitted force during lift'),
  ('cycle2_bottle_separation',13.1,13.3,'Bottle-card clearance visible; card stays on foam'),
  ('cycle2_card_only_recovery',13.3,15.031133333333335,'Ends at final decoded frame')],
 'fingertip':[
  ('reference',.2,1.2,'Bare yellow top; card is beside specimen'),
  ('central_contact',1.6,1.8,'Unknown finger force'),
  ('central_loading_and_deep_press',1.8,5.2,'Depth changes; no verified constant-force hold'),
  ('central_unloading',5.2,5.8,'Finger still in contact; force history unknown'),
  ('central_separation',5.8,6.,'Clear gap after conservative bound'),
  ('central_free_recovery',6.,6.5,'Before earliest possible next contact'),
  ('left_contact',6.5,6.8,'Unknown finger force'),
  ('left_loading_and_deep_press',6.8,8.7,'Large local deformation and broad opposite-side rise'),
  ('left_unloading',8.7,9.1,'Unknown changing contact force'),
  ('left_separation',9.1,9.4,'Conservative clearance bracket'),
  ('left_free_recovery',9.4,10.1,'Before earliest possible right contact'),
  ('right_contact',10.1,10.4,'Unknown finger force'),
  ('right_loading_and_deep_press',10.4,12.7,'Depth/position vary; no constant-force hold'),
  ('right_unloading',12.7,13.5,'Unknown changing contact force'),
  ('right_separation',13.5,13.7,'Clear gap by conservative bound'),
  ('right_free_recovery',13.7,14.664644444444445,'Ends at last decoded frame')]}


def run():
    phase_rows=[];peaks=[];decay=[];quality=[];reference_rows=[];recovery=[];holds=[]
    for slug,conf in CONFIG.items():
        folder=OUT/slug;d=pd.read_csv(folder/'measurements.csv');q=pd.read_csv(folder/'profiles.csv');cal=json.loads((folder/'calibration.json').read_text());poly=np.array(cal['y_to_relative_mm_polynomial'])
        for label,a,b,note in EVENTS[slug]:
            i=int(np.searchsorted(d.time_s,a,side='left'));j=min(len(d)-1,int(np.searchsorted(d.time_s,b,side='right')-1))
            phase_rows.append(dict(experiment=slug,event_or_phase=label,earliest_s=a,latest_s=b,first_frame_at_or_after_earliest=i,last_frame_at_or_before_latest=j,
                                   earliest_selected_pts_s=float(d.time_s.iloc[i]),latest_selected_pts_s=float(d.time_s.iloc[j]),evidence_note=note,force_measured=False))
        ref=pd.read_csv(folder/'reference_profile.csv')
        reference_rows.append(dict(experiment=slug,total_visible_height_mm=median(np.polyval(poly,ref.bottom_y_px)-np.polyval(poly,ref.top_y_px)),
                                   yellow_color_height_mm=median(np.polyval(poly,ref.yellow_bottom_y_px)-np.polyval(poly,ref.top_y_px)),
                                   green_color_height_mm=median(np.polyval(poly,ref.bottom_y_px)-np.polyval(poly,ref.green_top_y_px)),
                                   colored_face_span_px=(ref.x_px.iloc[-1]-ref.x_px.iloc[0])/.9,
                                   span_ruler_equivalent_mm=(ref.x_px.iloc[-1]-ref.x_px.iloc[0])/.9/cal['median_px_per_mm']))
        for label,a,b in conf['windows']:
            block=q[q.time_s.between(a,b)]
            for u in U:
                group=block[np.isclose(block.u_reference,u)];visible=group[~group.fingertip_occludes_true_top]
                points=d[d.time_s.between(a,b)];tip=median(points.tip_u_reference)
                decay.append(dict(experiment=slug,window=label,u_reference=float(u),samples=len(group),unoccluded_fraction=1-group.fingertip_occludes_true_top.mean(),
                                  visible_compression_mm=median(visible.visible_thickness_compression_mm),
                                  visible_compression_px=median(visible.visible_thickness_compression_px),
                                  threshold_range_mm=median(visible.threshold_height_range_mm),
                                  distance_from_visible_tip_image_fraction=abs(u-tip) if np.isfinite(tip) else np.nan))
        valid=q[~q.fingertip_occludes_true_top & q.top_visible_color_y_px.notna()]
        quality.append(dict(experiment=slug,frames=len(d),profile_attempts=len(q),missing_top_samples=int(q.top_visible_color_y_px.isna().sum()),
                            occluded_profile_samples=int(q.fingertip_occludes_true_top.sum()),registration_failures=int((~d.registration_valid).sum()),
                            registration_rms_median_px=median(d.registration_rms_px),registration_rms_max_px=d.registration_rms_px.max(),
                            registration_scale_min=d.registration_scale.min(),registration_scale_max=d.registration_scale.max(),
                            unoccluded_threshold_range_median_mm=median(valid.threshold_height_range_mm),
                            unoccluded_threshold_range_p95_mm=float(valid.threshold_height_range_mm.quantile(.95)),
                            unoccluded_threshold_range_max_mm=float(valid.threshold_height_range_mm.max())))
        ranges=[('central',1.8,5.8),('left',6.5,9.4),('right',10.1,13.7)] if slug=='fingertip' else []
        for label,a,b in ranges:
            block=d[d.time_s.between(a,b)];r=block.loc[block.tip_apparent_depth_mm.idxmax()]
            peaks.append(dict(experiment=slug,press=label,frame=int(r.frame),time_s=r.time_s,visible_tip_proxy_depth_px=r.tip_apparent_depth_px,
                               visible_tip_proxy_depth_mm=r.tip_apparent_depth_mm,tip_u_reference=r.tip_u_reference,
                               lower_finger_silhouette_width_px=r.low_right-r.low_left,depth_is_true_hidden_surface=False,force_N=np.nan))
        free=[('cycle1',7.2,8.8,'right'),('cycle2',13.3,float(d.time_s.iloc[-1]),'right')] if slug=='half_area' else [('central',6.,6.5,'center'),('left',9.4,10.1,'left'),('right',13.7,float(d.time_s.iloc[-1]),'right')]
        for label,a,b,region in free:
            key=f'{region}_region_compression_mm';early=d[d.time_s.between(a,a+.15)][key];late=d[d.time_s.between(b-.2,b)][key]
            recovery.append(dict(experiment=slug,cycle_or_press=label,region=region,start_after_latest_separation_s=a,end_before_next_contact_s=b,
                                 available_window_s=b-a,samples=int(d.time_s.between(a,b).sum()),
                                 initial_residual_mm=median(early),final_residual_mm=median(late),further_visible_recovery_mm=median(early)-median(late),
                                 timescale_identified=False))
        if slug=='half_area':
            for label,a,b in conf['windows']:
                if 'late_hold' not in label:continue
                block=d[d.time_s.between(a,b)];v=block.right_region_compression_mm
                holds.append(dict(window=label,start_s=a,end_s=b,first_frame=int(block.frame.iloc[0]),last_frame=int(block.frame.iloc[-1]),
                                  right_compression_median_mm=median(v),right_compression_range_mm=v.max()-v.min(),
                                  right_compression_std_mm=float(v.std()),right_compression_trend_mm_s=float(np.polyfit(block.time_s,v,1)[0]),
                                  hands_visible_in_cropped_view=False,hands_off_independently_verified=False,constant_force_verified=False))
    write_csv(OUT/'phases.csv',phase_rows);write_csv(OUT/'fingertip_peaks.csv',peaks);write_csv(OUT/'spatial_decay.csv',decay)
    write_csv(OUT/'measurement_quality.csv',quality);write_csv(OUT/'reference_geometry.csv',reference_rows);write_csv(OUT/'recovery_observations.csv',recovery);write_csv(OUT/'hold_quality.csv',holds)
    write_csv(OUT/'load_assumptions.csv',[dict(experiment='half_area',water_ml_reported_approx=1000,water_density_assumed_g_ml=1,tare_assumed_g=t,
      conditional_supported_force_N=(1000+t)*.00981,force_measured=False,total_bottle_mass_measured=False,pressure_distribution_known=False) for t in [50,75,100]]+
      [dict(experiment='fingertip',water_ml_reported_approx=np.nan,water_density_assumed_g_ml=np.nan,tare_assumed_g=np.nan,
            conditional_supported_force_N=np.nan,force_measured=False,total_bottle_mass_measured=False,pressure_distribution_known=False)])
    # Human-read apparent card/front-face geometry on the saved original frames.
    # Endpoints are approximate +/-15 px picks, not a calibrated 3D contact polygon.
    geometry=[]
    for index,foam_l,foam_r,card_l,yl,card_r,yr in [(0,350,1380,850,207,1610,225),(125,365,1370,880,393,1620,420),(330,365,1370,855,416,1615,435)]:
        frame=cv2.imread(str(OUT/'half_area'/f'selected_{index:05d}_original.jpg'));assert frame is not None
        cv2.line(frame,(card_l,yl),(card_r,yr),(255,0,255),3)
        for x in [foam_l,foam_r]:cv2.line(frame,(x,170),(x,650),(0,220,255),2)
        cv2.putText(frame,'Manual projected geometry only; +/-15px; depth overlap unknown',(30,80),0,.8,(0,0,255),2)
        cv2.imwrite(str(OUT/'half_area'/f'geometry_{index:05d}.jpg'),frame)
        fraction=(foam_r-card_l)/(foam_r-foam_l)
        geometry.append(dict(frame=index,foam_left_px=foam_l,foam_right_px=foam_r,card_left_px=card_l,card_left_y_px=yl,card_right_px=card_r,card_right_y_px=yr,
                             apparent_front_overlap_fraction=fraction,overhang_ruler_equivalent_mm=(card_r-foam_r)/15,
                             projected_card_edge_angle_deg=float(np.degrees(np.arctan2(yr-yl,card_r-card_l))),manual_endpoint_allowance_px=15,
                             conditional_area_mm2_if_full_50mm_depth=fraction*73*50,true_contact_area_identified=False))
    write_csv(OUT/'half_area'/'manual_geometry.csv',geometry)
    # Exact peak-frame evidence, selected by the recorded proxy rather than by seeking.
    folder=OUT/'fingertip';reference=cv2.imread(str(folder/'selected_00000_original.jpg'));gray,points=background(reference)
    wanted={r['frame']:r for r in peaks};cap=cv2.VideoCapture(str(ROOT/'Videos/fingertip.mp4'),cv2.CAP_FFMPEG,[cv2.CAP_PROP_N_THREADS,2]);index=0
    while wanted:
        ok,frame=cap.read();assert ok
        if index in wanted:
            row=wanted.pop(index);registered,info=register(frame,gray,points);assert registered is not None
            d=pd.read_csv(folder/'measurements.csv').iloc[index]
            cv2.imwrite(str(folder/f'peak_{row["press"]}_{index:05d}_original.jpg'),frame)
            cv2.circle(registered,(round(d.tip_x),round(d.tip_y)),10,(0,0,255),3)
            cv2.putText(registered,f'{row["press"]} frame {index}, t={row["time_s"]:.3f}s; visible-tip proxy {row["visible_tip_proxy_depth_mm"]:.1f}mm',(20,45),0,.7,(0,0,255),2)
            cv2.putText(registered,'Not true hidden-surface depth; fingertip force UNKNOWN',(20,1000),0,.8,(0,0,255),2)
            cv2.imwrite(str(folder/f'peak_{row["press"]}_{index:05d}_annotated.jpg'),registered)
        index+=1
    cap.release()
    limitations=[
      ('vertical_metric','40 / 31 ruler ticks; fit RMS 0.024 / 0.030 mm','Ruler-plane metric is not specimen-face calibration; assume separate +/-10% sensitivity only, not a guaranteed bound'),
      ('boundary_localization','2 px sampling lattice; unoccluded threshold-range p95 0.41 / 0.28 mm','Practical floor 0.3 mm; use larger pointwise threshold allowance where needed; extremes exceed 2 mm'),
      ('registration','Median inlier RMS 0.80 / 0.53 px; fitted scale varies about 2%','Ruler/background plane motion cannot isolate camera parallax or material motion'),
      ('profile_coordinates','Fixed image columns, 19 face fractions','Eulerian color/silhouette envelopes, not Lagrangian point displacement; edge-dominated 5% bins excluded from profile plots'),
      ('finger_depth','Peak visible-tip proxies 238.5 / 218 / 246 px','True surface hidden by fingertip; contact-point proxy only, no force or stiffness identification'),
      ('contact_area','Projected half-card overlap about 0.49-0.51 of face width','Depth overlap and actual bearing/contact patch unmeasured; conditional area is not measured area'),
      ('card_angle','Manual projected front-edge angles about 1.4-2.1 degrees; endpoint picks +/-15px','Angle uncertainty is order 2 degrees; cannot establish 3D horizontality/tilt or exclude card bending'),
      ('bottle_force','User reports approximately 1000ml water; tare assumed 50-100g','10.30-10.79N is conditional bookkeeping, not measured force or a guaranteed uncertainty interval'),
      ('hands_off_and_hold','Candidate hold compression ranges 1.09 / 1.36mm','Bottle top/hand may be outside view; stationary appearance does not prove constant or hands-off loading'),
      ('green_backing','Apparent green thickness decreases roughly 1-1.25mm during deep loading','Color boundary, perspective, fibres and nonuniform shear confounded; no backing modulus identified'),
      ('recovery','Post-separation changes about 0.34/0.68mm for half-card and 0.05-0.13mm for finger','Short windows, drift, uncertain release force and unknown final offset; no recovery timescale/damping estimated')]
    write_csv(OUT/'uncertainty_limitations.csv',(dict(quantity=k,evidence=e,limitation=l) for k,e,l in limitations))
    validation=[
      ('local_indentation_depth','partial: visible contact/contour proxy only','Unknown hidden center surface and depth-plane motion'),
      ('vertical_deformation_profile','half-area: useful front-face envelope; finger: partial outside occlusion','Not a 3D top surface or tracked material displacement'),
      ('spatial_deformation_decay','partial qualitative/1D image evidence','Cannot validate radial 3D decay or fit a constitutive length scale'),
      ('overall_load_reaction','not independently measured','Half-card gravity load conditional; finger force entirely unknown'),
      ('contact_geometry','partial projected location/span','True area, pressure and out-of-plane tilt unmeasured'),
      ('recovery_shape','qualitative return and residual profiles supported','No validated physical recovery speed or damping')]
    write_csv(OUT/'validation_capabilities.csv',(dict(quantity=k,supported=e,limitation=l) for k,e,l in validation))
    preserved=json.loads((OUT/'baseline_provenance.json').read_text())['protected_sha256'];assert all(sha(ROOT/p)==h for p,h in preserved.items())
    print('PASS: observations summarized; baseline hashes unchanged.')


if __name__=='__main__':run()
