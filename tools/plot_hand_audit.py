from pathlib import Path
import numpy as np,json
from PIL import Image,ImageDraw
root=Path(__file__).resolve().parents[1];folder=root/'outputs/hand-audit'
data=np.load(folder/'Left.npz');p=data['positions'];w=data['weights'];groups=data['groups'];bones=json.loads((folder/'audit.json').read_text())['bones']
colors=['#e25050','#49a86a','#397bc2','#be6dd1','#d49b30'];fingers=['Thumb','Index','Middle','Ring','Pinky']
im=Image.new('RGB',(1500,600),'white');draw=ImageDraw.Draw(im)
for panel,(a,b) in enumerate([(0,2),(1,2),(0,1)]):
    lo=p[:,[a,b]].min(axis=0);hi=p[:,[a,b]].max(axis=0);scale=470/max(hi-lo)
    def xy(v):return (int(panel*500+20+(v[a]-lo[0])*scale),int(550-(v[b]-lo[1])*scale))
    for i in range(0,len(p),2):
        dominant=groups[w[i].argmax()];color='#aaaaaa'
        for f,c in zip(fingers,colors):
            if f in dominant:color=c
        draw.point(xy(p[i]),fill=color)
    for name,seg in bones.items():
        if not name.startswith('LeftHand'):continue
        color='black'
        for f,c in zip(fingers,colors):
            if f in name:color=c
        x,y=xy(seg['head']);draw.line([xy(seg['head']),xy(seg['tail'])],fill=color,width=3);draw.ellipse([x-3,y-3,x+3,y+3],fill='black')
    draw.text((panel*500+20,10),f'Left hand projection {a}/{b}',fill='black')
im.save(folder/'weights-bones.png')
