"""Prepare editable reference planes; does not claim to reconstruct a mesh."""
import bpy,math,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'assets/3d/custom-v2/ReferenceWoman_Aligned.blend'))
collection=bpy.data.collections.new('HIGH_FIDELITY_REFERENCE_PLANES')
bpy.context.scene.collection.children.link(collection)
folder=ROOT/'assets/3d/high-fidelity-inputs'
for name,position,rotation in [
    ('front',(0,.30,.825),(math.pi/2,0,0)),
    ('back',(0,-.35,.825),(math.pi/2,0,math.pi)),
    ('left',(-.35,0,.825),(math.pi/2,0,math.pi/2)),
    ('right',(.35,0,.825),(math.pi/2,0,-math.pi/2))]:
    image=bpy.data.images.load(str(folder/(name+'.png')));image.pack()
    obj=bpy.data.objects.new('REFERENCE_'+name,None);collection.objects.link(obj)
    obj.empty_display_type='IMAGE';obj.data=image;obj.empty_display_size=1.722
    obj.location=position;obj.rotation_euler=rotation;obj.color[3]=.45
    obj.empty_image_depth='BACK';obj.hide_render=True
    obj['purpose']='Reference alignment only; photographs are not generated geometry.'
scene=bpy.context.scene
scene['HIGH_FIDELITY_STATUS']='Preparation only. Current visible mesh is V2 placeholder, not high-fidelity reconstruction.'
scene['NEXT']='Import approved reconstruction result; check clean head/hand topology, separate fingers, UV and materials before binding.'
out=ROOT/'outputs/high-fidelity';out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(out/'HighFidelity_Workbench.blend'))
print('Reference workbench saved, no new reconstructed mesh generated.')
