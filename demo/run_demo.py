"""Solve and render a frozen-model sequence and real/FEM comparisons. No fitting.

Run: python -B demo/run_demo.py
"""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import csv
import hashlib
import json
import shutil
import time
import cv2
import numpy as np
from PIL import Image
from demo.model import ROOT,configuration,digest,new_sponge,solve
from demo.render import equilibrium_frame,comparison_frame,text_frame

OUT=Path(__file__).resolve().parent/'outputs'


def write_csv(name,rows):
    rows=list(rows)
    with (OUT/name).open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def protected_hashes():
    return {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
            for folder in ['analysis','Videos','Assignment','Papers'] for p in sorted((ROOT/folder).rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts}


def extract_hold_frames(observations):
    """Read only selected showcase frames by sequential decode; no re-extraction of measurements."""
    result={};manifest=[];cv2.setNumThreads(2)
    for volume in [500,750,1000]:
        video=f'{volume}ml';rows=[r for r in observations if r['video']==video]
        targets={int((int(r['hold_start_frame'])+int(r['hold_end_frame']))//2):r for r in rows}
        with (ROOT/f'analysis/outputs/{video}/measurements.csv').open() as f:measurements=list(csv.DictReader(f))
        cap=cv2.VideoCapture(str(ROOT/f'Videos/{video}.mp4'),cv2.CAP_FFMPEG,[cv2.CAP_PROP_N_THREADS,2])
        index=0
        while targets:
            ok,frame=cap.read()
            if not ok:raise RuntimeError('Video ended before selected hold frame')
            if index in targets:
                row=targets.pop(index);pts=cap.get(cv2.CAP_PROP_POS_MSEC)/1000
                assert int(measurements[index]['frame'])==index and abs(pts-float(measurements[index]['time_s']))<1e-6
                crop=frame[120:810,150:1720];name=f'real_{video}_cycle{row["cycle"]}.jpg'
                if not cv2.imwrite(str(OUT/name),crop,[cv2.IMWRITE_JPEG_QUALITY,94]):raise RuntimeError('Image write failed')
                info=dict(video=video,cycle=int(row['cycle']),file=name,frame=index,time_s=pts,
                          hold_start_s=float(row['hold_start_s']),hold_end_s=float(row['hold_end_s']),
                          crop_original_xyxy='150,120,1720,810',measured_hold_median_mm=float(row['hold_compression_mm']))
                manifest.append(info);result[(volume,int(row['cycle']))]=(cv2.cvtColor(crop,cv2.COLOR_BGR2RGB),info)
            index+=1
        cap.release()
    write_csv('real_frame_manifest.csv',manifest)
    return result


def encode(frames,durations):
    """Cadence is for presentation only, never simulated time."""
    fps=10;writer=cv2.VideoWriter(str(OUT/'demonstration.mp4'),cv2.VideoWriter_fourcc(*'mp4v'),fps,(1280,720))
    if not writer.isOpened():raise RuntimeError('Installed OpenCV mp4v encoder unavailable')
    manifest=[];frame_index=0
    for i,(frame,duration) in enumerate(zip(frames,durations)):
        count=round(duration*fps)
        for _ in range(count):writer.write(cv2.cvtColor(frame,cv2.COLOR_RGB2BGR))
        manifest.append(dict(scene=i,first_encoded_frame=frame_index,encoded_frames=count,
                             presentation_duration_s=count/fps,physical_time_s='not defined'))
        frame_index+=count
    writer.release();write_csv('video_frame_manifest.csv',manifest)
    save_gif(frames,durations)
    cap=cv2.VideoCapture(str(OUT/'demonstration.mp4'));decoded=0
    while True:
        ok,frame=cap.read()
        if not ok:break
        assert frame.shape[:2]==(720,1280);decoded+=1
    cap.release();assert decoded==frame_index
    with Image.open(OUT/'demonstration.gif') as gif:assert gif.n_frames==len(frames)
    return dict(codec='OpenCV mp4v / MPEG-4 Part 2; GIF is browser fallback',encoded_frames=decoded,
                fps_presentation_only=fps,presentation_seconds=decoded/fps,unique_scenes=len(frames))


def save_gif(frames,durations):
    # A title-only palette loses yellow/green. Sample every scene so real photographs
    # and all mechanical components share a representative fixed color palette.
    columns=8;sheet=Image.new('RGB',(columns*160,90*int(np.ceil(len(frames)/columns))),'white')
    for i,frame in enumerate(frames):sheet.paste(Image.fromarray(frame).resize((160,90)),((i%columns)*160,(i//columns)*90))
    palette=sheet.quantize(colors=256)
    images=[Image.fromarray(f).quantize(palette=palette) for f in frames]
    images[0].save(OUT/'demonstration.gif',save_all=True,append_images=images[1:],duration=[round(d*1000) for d in durations],loop=0,optimize=False,disposal=2)


def run():
    start=time.perf_counter();OUT.mkdir(exist_ok=True);before=protected_hashes()
    config=configuration();sponge=new_sponge(config)
    (OUT/'frozen_models.json').write_text(json.dumps({n:configuration(n) for n in ['primary','alpha20']},indent=2)+'\n')
    with (ROOT/'analysis/outputs/cycle_summary.csv').open() as f:observations=list(csv.DictReader(f))
    nominal=(np.array([500,750,1000])+75)*.00981
    up=np.r_[np.linspace(0,nominal[0],13),np.linspace(nominal[0],nominal[1],8)[1:],np.linspace(nominal[1],nominal[2],8)[1:]]
    forces=np.r_[up,np.linspace(nominal[2],0,25)[1:]]
    key={0:'Undeformed reference',12:'500 ml equilibrium',19:'750 ml equilibrium',26:'1000 ml equilibrium',50:'Unloaded equilibrium'}
    states=[];rows=[];nodes=[]
    for i,force in enumerate(forces):
        state=solve(sponge,float(force));states.append(state)
        rows.append(dict(step=i,branch='loading' if i<len(up) else 'unloading',label=key.get(i,'Intermediate equilibrium'),
                         force_N=force,compression_mm=state.displacement*1000,min_J=state.min_J,max_J=state.max_J,
                         free_residual_N=state.free_residual,reaction_N=state.top_reaction,force_error_N=state.top_reaction-force,
                         top_bottom_balance_N=state.top_reaction-state.bottom_reaction,energy_J=state.energy,termination=state.termination))
        nodes.extend(dict(step=i,node=j,x_m=p[0],y_m=p[1],z_m=p[2]) for j,p in enumerate(state.positions))
    assert np.all(np.diff([r.displacement for r in states[:len(up)]])>0)
    assert np.all(np.diff([r.displacement for r in states[len(up)-1:]])<0)
    recovery_error=float(np.max(abs(states[-1].positions-sponge.solver.X)));assert recovery_error<3e-8
    np.savez_compressed(OUT/'solved_fem_states.npz',reference_m=sponge.solver.X,cells=sponge.solver.cells,
                        boundary=sponge.boundary,forces_N=forces,positions_m=np.stack([s.positions for s in states]),
                        compression_m=np.array([s.displacement for s in states]),backing_m=sponge.backing_vertices)
    write_csv('equilibria.csv',rows);write_csv('solved_nodes.csv',nodes)
    photos=extract_hold_frames(observations)
    frames=[text_frame('SoftBodyDynamics | Predictive FEM demonstration',[
        ('A sponge observed in three compression videos',22,'#15283b'),
        ('One fitted scale: mu = 6999.815 Pa; alpha = 10 and beta = 0 assumed',18,'#1865ad'),
        ('Only first 500 / 1000 ml cycles calibrated the model',18,'#15283b'),
        ('750 ml is held out from this FEM fit, not prospective validation',18,'#a14f18'),
        ('All yellow vertices below come from force-controlled FEM equilibria',18,'#15283b')])]
    durations=[4.];path=[(float(f),1000*s.displacement) for f,s in zip(up,states)]
    stills={}
    for i,(force,state) in enumerate(zip(forces,states)):
        title=key.get(i,'Loading: intermediate equilibrium' if i<len(up) else 'Unloading: intermediate equilibrium')
        frame=equilibrium_frame(sponge,state,float(force),i,len(states),path,'loading' if i<len(up) else 'unloading',title)
        frames.append(frame);durations.append(2. if i in key else .2)
        if i in key:
            filename={0:'reference',12:'500ml',19:'750ml',26:'1000ml',50:'unloaded'}[i]
            Image.fromarray(frame).save(OUT/f'fem_{filename}.png');stills[filename]=frame
    for volume,index in [(500,12),(750,19),(1000,26)]:
        xx=[float(r['hold_compression_mm']) for r in observations if r['video']==f'{volume}ml']
        photo,info=photos[(volume,1)];frame=comparison_frame(sponge,states[index],volume,photo,info,xx)
        Image.fromarray(frame).save(OUT/f'comparison_{volume}ml.png');frames.append(frame);durations.append(4.)
    # The Stage 5 plot already contains actual FEM and baseline model predictions.
    shutil.copyfile(ROOT/'analysis/calibration/outputs/force_compression.png',OUT/'force_compression.png')
    plot=np.array(Image.open(OUT/'force_compression.png').convert('RGB'))
    canvas=Image.new('RGB',(1280,720),'white');image=Image.fromarray(plot);image.thumbnail((1260,700));canvas.paste(image,((1280-image.width)//2,(720-image.height)//2))
    frames.append(np.array(canvas));durations.append(5.)
    frames.append(text_frame('What this model demonstrates - and what remains open',[
        ('Numerically verified 3D mechanics; observation-calibrated equilibrium scale',19,'#15283b'),
        ('Primary calibration RMSE 0.800 mm; 750 ml RMSE 0.504 mm',19,'#1865ad'),
        ('Empirical interpolation: 750 ml RMSE 0.490 mm; no FEM accuracy advantage',18,'#15283b'),
        ('Unloading is reversible equilibrium, not a prediction of recovery speed',18,'#a14f18'),
        ('Still needed: fresh measured interaction and resolved release/recovery data',18,'#a14f18')]))
    durations.append(5.)
    encoding=encode(frames,durations)
    comparison=[]
    with (ROOT/'analysis/calibration/outputs/predictions.csv').open() as f:prior=list(csv.DictReader(f))
    for volume,index in [(500,12),(750,19),(1000,26)]:
        for cycle in [1,2]:
            source=next(r for r in observations if r['video']==f'{volume}ml' and int(r['cycle'])==cycle)
            predicted=1000*states[index].displacement
            old=next(r for r in prior if r['model']=='primary' and r['video']==source['video'] and int(r['cycle'])==cycle)
            assert abs(predicted-float(old['predicted_mm']))<2e-5
            comparison.append(dict(video=source['video'],cycle=cycle,role=old['split'],force_N=float(forces[index]),
                                   observed_mm=float(source['hold_compression_mm']),predicted_mm=predicted,
                                   residual_mm=predicted-float(source['hold_compression_mm'])))
    write_csv('comparison.csv',comparison)
    assert before==protected_hashes(),'Previous-stage or original input changed'
    (OUT/'preserved_sha256.json').write_text(json.dumps(before,indent=2)+'\n')
    summary=dict(status='PASS',model_sha256=digest(config),equilibria=len(states),nodes=len(sponge.solver.X),tetrahedra=len(sponge.solver.cells),
                 max_free_residual_N=max(s.free_residual for s in states),min_J=min(s.min_J for s in states),
                 max_force_error_N=max(abs(r['force_error_N']) for r in rows),max_top_bottom_balance_N=max(abs(r['top_bottom_balance_N']) for r in rows),
                 unloaded_reference_error_m=recovery_error,protected_files_unchanged=len(before),encoding=encoding,
                 runtime_seconds=time.perf_counter()-start,no_fresh_experiment_available=True,no_physical_recovery_timescale=True)
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    write_viewer(comparison,summary)
    print(json.dumps(summary,indent=2))


def write_viewer(comparison,summary):
    table=''.join(f'<tr><td>{r["video"]}/{r["cycle"]}</td><td>{r["role"]}</td><td>{r["observed_mm"]:.3f}</td><td>{r["predicted_mm"]:.3f}</td><td>{r["residual_mm"]:+.3f}</td></tr>' for r in comparison)
    html='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SoftBodyDynamics | Frozen FEM</title>
<style>body{margin:0;background:#f3f5f8;color:#14283c;font:17px/1.6 system-ui}main{max-width:1120px;margin:auto;padding:40px 24px}h1{font-size:40px;line-height:1.15}h2{margin-top:42px}img,video{max-width:100%;border-radius:10px;background:white}section{background:white;padding:24px;border-radius:14px;margin:24px 0}a{color:#1768ac}table{border-collapse:collapse;width:100%;font-size:14px}th,td{text-align:left;border-bottom:1px solid #dce3eb;padding:10px}.note{border-left:5px solid #d98b26;padding:15px;background:#fff5e8}.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}@media(max-width:700px){.grid{display:block}h1{font-size:30px}}small{color:#526376}summary{cursor:pointer;font-weight:bold}</style>
<main><small>DIRAC ROBOTICS TAKE-HOME | STAGE 6</small><h1>From video observations to<br>force-driven 3D equilibrium</h1>
<p>A frozen one-scale hyperfoam FEM model of the yellow sponge above rigid green backing. No measured marker trajectory drives its vertices.</p>
<p class="note"><strong>Scope:</strong> quasi-static loading and reversible unloading. Playback cadence is illustrative, not measured recovery time. Existing 750 ml data are held out of this FEM fit, not untouched prospective validation.</p>
<h2>Demonstration</h2><p><a href="demonstration.mp4" download>Download MP4</a> (MPEG-4 Part 2) · <a href="demonstration.gif">Open GIF</a> · <a href="../../README.md">Run instructions</a></p>
<details open><summary>Play animation (GIF browser fallback)</summary><img src="demonstration.gif" alt="Force-controlled FEM loading and unloading, followed by real specimen comparisons"></details>
<h2>Real specimen and simulated equilibria</h2><p>Real photographs show one frame within each first-cycle hold. Measurements are settled-window medians, not measurements of the displayed individual frame. Cameras are not pixel registered.</p>
<img src="comparison_500ml.png" alt="500 ml calibration comparison"><img src="comparison_750ml.png" alt="750 ml held-out-from-fit comparison"><img src="comparison_1000ml.png" alt="1000 ml calibration comparison">
<section><h2>Quantitative comparison</h2><table><tr><th>Load/cycle</th><th>Role</th><th>Measured mm</th><th>FEM mm</th><th>Error mm</th></tr>TABLE</table>
<p>Primary: mu = 6999.814990181902 Pa, alpha = 10, beta = 0. Calibration RMSE 0.800 mm; 750 ml RMSE 0.504 mm, versus 0.490 mm for empirical interpolation. The primary low-load mismatch exceeds its nominal engineering allowance.</p></section>
<img src="force_compression.png" alt="Force-compression comparison including primary FEM, labeled alpha20 sensitivity, empirical baseline and all six observations">
<section><h2>What is established?</h2><p>Element energies/gradients, force equilibrium, positive Jacobians and coordinate/mesh consistency are numerically verified. Videos inform an effective global equilibrium scale. Spatial stresses, lateral expansion, arbitrary contact and dynamic recovery have not been experimentally validated.</p>
<p>Alpha = 20 remains a sensitivity comparison: it fits the two endpoints better but has larger 750 ml error. The data do not identify a unique constitutive shape. The green backing is assumed rigid; normal constraints are full-face frictionless planes, not a collision solver.</p>
<p>No fresh validation experiment is available. <a href="../FRESH_VALIDATION.md">Predict first, measure and score later</a>; the frozen evaluator never refits.</p></section>
<section><h2>Reproduce and inspect</h2><p><a href="equilibria.csv">51 equilibrium records</a> · <a href="solved_fem_states.npz">Solved nodal arrays/connectivity</a> · <a href="real_frame_manifest.csv">Real frame identities/timestamps</a> · <a href="summary.json">Numerical summary</a> · <a href="../TECHNICAL_SUMMARY.md">Technical interpretation and assignment gaps</a></p>
<p>Input videos: <a href="../../Videos/500ml.mp4">500 ml</a> · <a href="../../Videos/750ml.mp4">750 ml</a> · <a href="../../Videos/1000ml.mp4">1000 ml</a>. All originals and prior analysis artifacts were preserved.</p></section></main></html>'''
    (OUT/'index.html').write_text(html.replace('TABLE',table),encoding='utf-8')


if __name__=='__main__':run()
