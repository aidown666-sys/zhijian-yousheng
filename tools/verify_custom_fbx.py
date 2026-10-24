import bpy,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
path=ROOT/'assets/3d/custom/ReferenceWoman_Prototype.fbx'
bpy.ops.import_scene.fbx(filepath=str(path))
arms=[o for o in bpy.context.scene.objects if o.type=='ARMATURE']
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
assert len(arms)==1
arm=arms[0]
required=[f'{side}Hand{finger}{joint}' for side in ['Left','Right'] for finger in ['Thumb','Index','Middle','Ring','Pinky'] for joint in [1,2,3]]
missing=[n for n in required if n not in arm.data.bones]
unbound=[o.name for o in meshes if not any(m.type=='ARMATURE' and m.object==arm for m in o.modifiers)]
report={'passed':not missing and not unbound,'bones':len(arm.data.bones),'finger_joints_checked':len(required),
        'mesh_objects':len(meshes),'missing_finger_bones':missing,'unbound_meshes':unbound,
        'actions':len(bpy.data.actions),'images':[{'name':i.name,'packed':bool(i.packed_file),'size':list(i.size)} for i in bpy.data.images if i.type=='IMAGE'],
        'scope':'FBX roundtrip structure only; not likeness or signing accuracy'}
(ROOT/'outputs/custom-avatar/fbx-verification.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps(report));assert report['passed']
