import bpy,json
from pathlib import Path
from mathutils import Vector
root=Path(__file__).resolve().parents[1]
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.fbx(filepath=str(root/'assets/3d/valid/Asian_F_1_Busi.fbx'))
out=root/'outputs/custom-avatar';out.mkdir(parents=True,exist_ok=True)
report={}
for o in bpy.context.scene.objects:
    if o.type=='MESH':
        pts=[o.matrix_world@Vector(p) for p in o.bound_box]
        report[o.name]={'min':[min(p[i] for p in pts) for i in range(3)],'max':[max(p[i] for p in pts) for i in range(3)]}
    if o.type=='ARMATURE':
        report['bones']={b.name:list(o.matrix_world@b.head_local) for b in o.data.bones if b.name in ['Head','Neck','LeftHand','LeftArm','RightHand','Hips']}
for image in bpy.data.images:
    if image.name.endswith('_color.jpg'):
        image.filepath_raw=str(out/'base-color.png');image.file_format='PNG';image.save()
(out/'inspection.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
