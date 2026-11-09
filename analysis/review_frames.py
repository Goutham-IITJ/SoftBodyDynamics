"""Generate traceable contact/separation contact sheets for manual annotation.
Run: python analysis/review_frames.py
Uses decoded PTS/frame indices, not assumed constant-rate timestamps.
"""
import json
import csv
from pathlib import Path
import cv2
import numpy as np

HERE=Path(__file__).resolve().parent
CONFIG=json.loads((HERE/'config.json').read_text())
OUT=HERE/'outputs'/'manual_review'
OUT.mkdir(parents=True,exist_ok=True)
cv2.setNumThreads(2)
manifest=[]
for name,conf in CONFIG['videos'].items():
    cap=cv2.VideoCapture(str(HERE.parent/conf['path']),cv2.CAP_FFMPEG,[cv2.CAP_PROP_N_THREADS,2])
    requests=[]
    groups={}
    for cycle in conf['cycles']:
        for event in ['contact','separation']:
            low,high=cycle[event]
            requested=np.linspace(low-.15,high+.15,16)
            key=f'{name}_cycle{cycle["id"]}_{event}'
            groups[key]=[]
            requests.extend((float(t),key,event) for t in requested)
    requests.sort(); request_index=0; idx=0
    ok,frame=cap.read()
    while ok and request_index<len(requests):
        pts=cap.get(cv2.CAP_PROP_POS_MSEC)/1000
        while request_index<len(requests) and pts>=requests[request_index][0]:
                _,key,event=requests[request_index]
                tile=cv2.resize(frame[:620,150:1720],(628,248))
                cv2.putText(tile,f'{name} {event} t={pts:.3f} f={idx}',(5,20),0,.5,(0,0,255),1)
                groups[key].append(tile); request_index+=1
                manifest.append({'sheet':key+'.jpg','tile_index_zero_based':len(groups[key])-1,'video':name,'frame':idx,'time_s':pts})
        idx+=1; ok,frame=cap.read()
    cap.release()
    for key,tiles in groups.items():
        while len(tiles)%4: tiles.append(np.zeros_like(tiles[0]))
        cv2.imwrite(str(OUT/f'{key}.jpg'),np.vstack([np.hstack(tiles[i:i+4]) for i in range(0,len(tiles),4)]))
with (OUT/'frame_manifest.csv').open('w',newline='') as stream:
    writer=csv.DictWriter(stream,fieldnames=list(manifest[0])); writer.writeheader(); writer.writerows(manifest)
