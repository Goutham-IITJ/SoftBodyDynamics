"""Phase 7A sequential inventory/contact sheets; does not change prior analyses."""
from pathlib import Path
import csv,hashlib,json,subprocess
import cv2
import numpy as np

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OUT=HERE/'outputs'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def write_csv(path,rows):
    rows=list(rows)
    with path.open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def inspect():
    OUT.mkdir(exist_ok=True);cv2.setNumThreads(2)
    tag='baseline-v1-fullface-fem'
    entries=[e for e in subprocess.check_output(['git','ls-tree','-r','-z',tag],cwd=ROOT).split(b'\0') if e]
    protected={}
    for entry in entries:
        meta,name=entry.split(b'\t',1);path=name.decode();data=(ROOT/path).read_bytes()
        assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==meta.split()[2].decode(),f'Frozen baseline changed: {path}'
        protected[path]=hashlib.sha256(data).hexdigest()
    (OUT/'baseline_provenance.json').write_text(json.dumps(dict(baseline_commit=subprocess.check_output(['git','rev-parse',tag+'^{commit}'],cwd=ROOT,text=True).strip(),baseline_tag=tag,protected_sha256=protected),indent=2)+'\n')
    inventory=[];manifest=[]
    for slug,path in [('half_area',ROOT/'Videos/half area.mp4'),('fingertip',ROOT/'Videos/fingertip.mp4')]:
        folder=OUT/slug;folder.mkdir(exist_ok=True)
        cap=cv2.VideoCapture(str(path),cv2.CAP_FFMPEG,[cv2.CAP_PROP_N_THREADS,2]);reported=cap.get(cv2.CAP_PROP_FRAME_COUNT);fps=cap.get(cv2.CAP_PROP_FPS)
        rows=[];tiles=[];index=0;next_time=0
        while True:
            ok,frame=cap.read()
            if not ok:break
            height,width=frame.shape[:2]
            pts=cap.get(cv2.CAP_PROP_POS_MSEC)/1000
            rows.append(dict(frame=index,time_s=pts))
            if pts>=next_time:
                tile=cv2.resize(frame,(640,360));cv2.putText(tile,f'{slug} f={index} t={pts:.3f}s',(8,25),0,.65,(0,0,255),2)
                tiles.append(tile);manifest.append(dict(experiment=slug,sheet=f'{slug}/overview.jpg',tile=len(tiles)-1,frame=index,time_s=pts))
                cv2.imwrite(str(folder/f'frame_{index:05d}.jpg'),frame,[cv2.IMWRITE_JPEG_QUALITY,96])
                next_time+=.5
            index+=1
        cap.release();times=np.array([r['time_s'] for r in rows]);gaps=np.diff(times)
        assert np.all(gaps>0) and len(rows)==round(reported)
        write_csv(folder/'timestamps.csv',rows)
        while len(tiles)%4:tiles.append(np.full_like(tiles[0],255))
        cv2.imwrite(str(folder/'overview.jpg'),np.vstack([np.hstack(tiles[i:i+4]) for i in range(0,len(tiles),4)]))
        inventory.append(dict(experiment=slug,source=path.relative_to(ROOT).as_posix(),sha256=sha(path),bytes=path.stat().st_size,width=width,height=height,decoded_frames=len(rows),reported_frames=reported,reported_fps=fps,last_timestamp_s=times[-1],median_interval_s=np.median(gaps),largest_interval_s=gaps.max(),nonmonotonic_intervals=int(np.sum(gaps<=0))))
    write_csv(OUT/'inventory.csv',inventory);write_csv(OUT/'overview_manifest.csv',manifest)
    assert all(sha(ROOT/p)==h for p,h in protected.items())
    print(json.dumps(inventory,indent=2))


if __name__=='__main__':inspect()
