import os
import bpy,json,math
from pathlib import Path
bpy.ops.wm.read_factory_settings(use_empty=True)
folder=Path(os.environ.get('SIGNHUMAN_WORK_DIR', str(Path(__file__).resolve().parents[1]/'assets/3d/user/source')))
bpy.ops.import_scene.fbx(filepath=str(folder/'SignHuman_HandsOptimized.fbx'))
mesh=next(o for o in bpy.context.scene.objects if o.type=='MESH');arm=mesh.find_armature()
assert arm,'Missing skin skeleton'
assert all(b.length>.00001 for b in arm.data.bones if b.use_deform),'Zero length deform bone'
invalid=zero=0
deform={g.index for g in mesh.vertex_groups if g.name in arm.data.bones and arm.data.bones[g.name].use_deform}
for vertex in mesh.data.vertices:
    weights=[g.weight for g in vertex.groups if g.group in deform]
    invalid+=any(not math.isfinite(w) or w<0 for w in weights)
    zero+=sum(weights)<.001
assert not invalid and not zero,(invalid,zero)
for side in ['Left','Right']:
    for finger in ['Thumb','Index','Middle','Ring','Pinky']:
        for j in [1,2,3]:assert arm.data.bones[f'{side}Hand{finger}{j}'].use_deform
        end=mesh.vertex_groups.get(f'{side}Hand{finger}4')
        if end:assert sum(g.weight for v in mesh.data.vertices for g in v.groups if g.group==end.index)<.001,'End joint unexpectedly has skin weights'
report={'fbx_roundtrip':'passed','bones':len(arm.data.bones),'vertices':len(mesh.data.vertices),'invalid_weights':invalid,'unweighted':zero,'finger_layout':'3 weighted joints plus unweighted end; FBX import may reset use_deform flags'}
(folder/'verification.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps(report))
