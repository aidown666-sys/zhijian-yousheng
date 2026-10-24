import bpy,numpy as np,json
from pathlib import Path
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=r'C:\Users\admin\Desktop\3D\optimized\SignHuman_HandsOptimized.fbx')
obj=next(o for o in bpy.context.scene.objects if o.type=='MESH');arm=obj.find_armature()
P=np.array([obj.matrix_world@v.co for v in obj.data.vertices]);rows=[]
for finger in ['Thumb','Index','Middle','Ring','Pinky']:
    a=np.array(arm.matrix_world@arm.data.bones['LeftHand'+finger+'1'].head_local);b=np.array(arm.matrix_world@arm.data.bones['LeftHand'+finger+'3'].tail_local)
    for t in [.3,.6,.9]:
        indices=np.argsort(np.linalg.norm(P-(a+(b-a)*t),axis=1))[:10];groups={}
        for index in indices:
            for g in obj.data.vertices[int(index)].groups:
                name=obj.vertex_groups[g.group].name;groups[name]=groups.get(name,0)+g.weight/len(indices)
        rows.append({'finger':finger,'position':t,'weights':groups})
print(json.dumps(rows))
folder=Path(__file__).resolve().parents[1]/'outputs/hand-audit'
mask=np.linalg.norm(P-np.array(arm.matrix_world@arm.data.bones['LeftHand'].head_local),axis=1)<.25;ids=np.where(mask)[0];weights=np.zeros((len(ids),len(obj.vertex_groups)))
for j,i in enumerate(ids):
    for g in obj.data.vertices[int(i)].groups:weights[j,g.group]=g.weight
np.savez(folder/'Left-after.npz',positions=P[ids],weights=weights,ids=ids,groups=np.array([g.name for g in obj.vertex_groups]))
