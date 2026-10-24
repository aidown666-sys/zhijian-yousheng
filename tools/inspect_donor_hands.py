import bpy,json,struct
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
raw=(ROOT/'assets/3d/sample.vrm').read_bytes();length,kind=struct.unpack_from('<II',raw,12);metadata=json.loads(raw[20:20+length])
mapping={name:metadata['nodes'][x['node']]['name'] for name,x in metadata['extensions']['VRMC_vrm']['humanoid']['humanBones'].items()}
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(ROOT/'assets/3d/sample.vrm'))
arm=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
report={'mapping':mapping,'meshes':[],'bones':{}}
for name in ['leftLowerArm','leftHand','leftIndexProximal','leftMiddleProximal','leftLittleProximal']:
    b=arm.data.bones[mapping[name]];report['bones'][name]={'head':list(arm.matrix_world@b.head_local),'tail':list(arm.matrix_world@b.tail_local)}
for obj in bpy.context.scene.objects:
    if obj.type=='MESH':report['meshes'].append({'name':obj.name,'vertices':len(obj.data.vertices),'groups':[g.name for g in obj.vertex_groups if 'Hand' in g.name or 'Index' in g.name]})
(ROOT/'outputs/hand-audit/donor.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report))
