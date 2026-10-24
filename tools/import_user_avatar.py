import os
"""Inspect and package the user's supplied FBX without editing the source."""
import bpy,json
from mathutils.kdtree import KDTree
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(Path(os.environ.get('SIGNHUMAN_SOURCE_DIR', str(ROOT/'assets/3d/user/source')))/'SignHuman_Final.fbx'))
out=ROOT/'assets/3d/user';out.mkdir(parents=True,exist_ok=True)
report={'bones':[],'meshes':[],'images':[]}
for obj in list(bpy.context.scene.objects):
    if obj.type in ('LIGHT','CAMERA'):bpy.data.objects.remove(obj,do_unlink=True);continue
    if obj.type=='ARMATURE':report['bones']+=[b.name for b in obj.data.bones]
    if obj.type=='MESH':
        arm=obj.find_armature();deform={g.index for g in obj.vertex_groups if arm and g.name in arm.data.bones and arm.data.bones[g.name].use_deform}
        zero=[v.index for v in obj.data.vertices if sum(g.weight for g in v.groups if g.group in deform)<.001]
        report['meshes'].append({'name':obj.name,'vertices':len(obj.data.vertices),'groups':len(obj.vertex_groups),'armature':any(m.type=='ARMATURE' for m in obj.modifiers),'unweighted':len(zero)})
        if zero:
            invalid=set(zero);tree=KDTree(len(obj.data.vertices)-len(zero))
            for v in obj.data.vertices:
                if v.index not in invalid:tree.insert(v.co,v.index)
            tree.balance()
            for index in zero:
                _,near,_=tree.find(obj.data.vertices[index].co)
                weights=[(g.group,g.weight) for g in obj.data.vertices[near].groups if g.group in deform and g.weight>0]
                weights=sorted(weights,key=lambda x:-x[1])[:4];total=sum(w for _,w in weights)
                for group,weight in weights:obj.vertex_groups[group].add([index],weight/total,'REPLACE')
            report['meshes'][-1]['repaired_unweighted']=len(zero)
for image in bpy.data.images:
    report['images'].append({'name':image.name,'size':list(image.size),'packed':bool(image.packed_file)})
    if image.size[0]>2048 or image.size[1]>2048:image.scale(2048,2048)
bpy.ops.export_scene.gltf(filepath=str(out/'SignHuman_Final.glb'),export_format='GLB',export_animations=False)
(out/'inspection.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('USER_AVATAR_REPORT',json.dumps(report,ensure_ascii=True))
