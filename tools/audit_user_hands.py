import bpy,json,sys
import numpy as np
from pathlib import Path
root=Path(__file__).resolve().parents[1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=r'C:\Users\admin\Desktop\3D\SignHuman_Final.fbx')
mesh=next(o for o in bpy.context.scene.objects if o.type=='MESH');arm=mesh.find_armature()
points=np.array([mesh.matrix_world@v.co for v in mesh.data.vertices]);bones={b.name:{'head':list(arm.matrix_world@b.head_local),'tail':list(arm.matrix_world@b.tail_local)} for b in arm.data.bones}
report={'bones':bones,'vertex_count':len(points),'regions':{}}
out=root/'outputs/hand-audit';out.mkdir(parents=True,exist_ok=True)
for side in ['Left','Right']:
    wrist=np.array(bones[side+'Hand']['head']);mask=np.linalg.norm(points-wrist,axis=1)<.25
    ids=np.where(mask)[0];weights=np.zeros((len(ids),len(mesh.vertex_groups)))
    for j,i in enumerate(ids):
        for g in mesh.data.vertices[int(i)].groups:weights[j,g.group]=g.weight
    np.savez(out/(side+'.npz'),positions=points[ids],weights=weights,ids=ids,groups=np.array([g.name for g in mesh.vertex_groups]))
    finger=[g.index for g in mesh.vertex_groups if g.name.startswith(side+'Hand') and g.name!=side+'Hand']
    count=(weights[:,finger]>.05).sum(axis=1)
    report['regions'][side]={'points':len(ids),'multi_finger_groups':int((count>2).sum()),'weight_sum_min':float(weights.sum(axis=1).min()),'weight_sum_max':float(weights.sum(axis=1).max())}
(out/'audit.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps(report))
