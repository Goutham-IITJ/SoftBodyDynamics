"""Dense sequential event review; no seeking or modification of video/measurements."""
from inspect_videos import ROOT,OUT,write_csv
import cv2,numpy as np

WINDOWS={
 'half_area':('Videos/half area.mp4',[
  ('cycle1_contact',1.6,2.8),('cycle1_release',6.3,7.4),
  ('cycle2_contact',8.5,9.8),('cycle2_release',12.2,13.7)]),
 'fingertip':('Videos/fingertip.mp4',[
  ('central_contact',1.4,2.1),('central_release',5.2,6.1),('left_contact',6.4,7.2),
  ('left_release',8.6,9.9),('right_contact',9.9,10.8),('right_release',12.6,13.9)])}


def run():
    cv2.setNumThreads(2);manifest=[]
    for slug,(source,windows) in WINDOWS.items():
        cap=cv2.VideoCapture(str(ROOT/source),cv2.CAP_FFMPEG,[cv2.CAP_PROP_N_THREADS,2]);groups={key:[] for key,_,_ in windows};i=0
        while True:
            ok,frame=cap.read()
            if not ok:break
            t=cap.get(cv2.CAP_PROP_POS_MSEC)/1000
            if i%3==0:
                for key,a,b in windows:
                    if a<=t<=b:
                        tile=cv2.resize(frame[:700,250:1650],(700,350));cv2.putText(tile,f'{key}: f={i}, t={t:.3f}s',(8,24),0,.62,(0,0,255),2)
                        manifest.append(dict(experiment=slug,sheet=f'{slug}/{key}.jpg',tile=len(groups[key]),frame=i,time_s=t));groups[key].append(tile)
            i+=1
        cap.release()
        for key,tiles in groups.items():
            while len(tiles)%4:tiles.append(np.full_like(tiles[0],255))
            cv2.imwrite(str(OUT/slug/(key+'.jpg')),np.vstack([np.hstack(tiles[j:j+4]) for j in range(0,len(tiles),4)]))
    write_csv(OUT/'event_review_manifest.csv',manifest)


if __name__=='__main__':run()
