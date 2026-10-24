import os
import bpy,json,math
import numpy as np
from pathlib import Path
from mathutils import Matrix,Quaternion
folder=Path(os.environ.get('SIGNHUMAN_WORK_DIR', str(Path(__file__).resolve().parents[1]/'assets/3d/user/source')))
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(folder/'SignHuman_CleanHands.fbx'))
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH'];arm=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
report={'bones':len(arm.data.bones),'meshes':{},'poses':{}}
hands=[o for o in meshes if 'CleanHand' in o.name]
assert len(hands)==2
for obj in meshes:
    zero=invalid=0
    for v in obj.data.vertices:
        weights=[g.weight for g in v.groups]
        zero+=sum(weights)<.001;invalid+=any(not math.isfinite(w) or w<0 for w in weights)
    assert not zero and not invalid,(obj.name,zero,invalid)
    report['meshes'][obj.name]={'vertices':len(obj.data.vertices),'unweighted':zero,'invalid':invalid}
original={}
for obj in hands:
    edges=np.array([e.vertices[:] for e in obj.data.edges]);P=np.array([obj.matrix_world@v.co for v in obj.data.vertices]);lengths=np.linalg.norm(P[edges[:,0]]-P[edges[:,1]],axis=1);mask=lengths>.0002;original[obj.name]=(edges[mask],lengths[mask])
for pose in ['open','fist','point','wrist']:
    for pb in arm.pose.bones:pb.matrix_basis=Matrix.Identity(4)
    for side in ['Left','Right']:
        bones=arm.data.bones;normal=(bones[side+'HandIndex1'].head_local-bones[side+'HandPinky1'].head_local).cross(bones[side+'HandMiddle1'].head_local-bones[side+'Hand'].head_local).normalized()
        for finger in ['Thumb','Index','Middle','Ring','Pinky']:
            for j in (1,2,3):
                name=f'{side}Hand{finger}{j}';pb=arm.pose.bones[name];next=bones[f'{side}Hand{finger}{j+1}']
                along=(next.head_local-pb.bone.head_local).normalized();axis=pb.bone.matrix_local.to_quaternion().inverted()@along.cross(normal).normalized()
                angle=.65 if pose=='fist' or pose=='point' and finger!='Index' else 0
                pb.rotation_mode='QUATERNION';pb.rotation_quaternion=Quaternion(axis,angle)
        if pose=='wrist':arm.pose.bones[side+'Hand'].rotation_quaternion=Quaternion((0,1,0),.7)
    bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();report['poses'][pose]={}
    for obj in hands:
        evaluated=obj.evaluated_get(dg);me=evaluated.to_mesh();P=np.array([evaluated.matrix_world@v.co for v in me.vertices]);evaluated.to_mesh_clear();assert np.isfinite(P).all()
        edges,lengths=original[obj.name];ratio=np.linalg.norm(P[edges[:,0]]-P[edges[:,1]],axis=1)/lengths
        report['poses'][pose][obj.name]={'stretch_p99':round(float(np.percentile(ratio,99)),3),'edges_over_3x':int((ratio>3).sum())}
(folder/'clean-hands-verification.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report))
