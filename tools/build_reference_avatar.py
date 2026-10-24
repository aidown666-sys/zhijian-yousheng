"""Blender prototype: licensed rigged base + reference projection, not reconstruction."""
import bpy, math, json, shutil
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/custom-avatar';OUT.mkdir(parents=True,exist_ok=True)
ASSET=ROOT/'assets/3d/custom';ASSET.mkdir(parents=True,exist_ok=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.fbx(filepath=str(ROOT/'assets/3d/valid/Asian_F_1_Busi.fbx'))
for o in list(bpy.context.scene.objects):
    if o.type in ('LIGHT','CAMERA'):bpy.data.objects.remove(o,do_unlink=True)
arm=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
main=bpy.data.objects['H_DDS_HighRes']
reference=ASSET/'reference-sheet.png'
shutil.copy2(r'C:\Users\admin\AppData\Local\Temp\codex-clipboard-c6051bd5-e804-4029-b0ba-963b4df5ff4d.png',reference)
ref=bpy.data.images.load(str(reference));ref.pack()
# UV projection stores only the front portrait region of the supplied sheet.
uv=main.data.uv_layers.new(name='ReferenceProjection')
for loop in main.data.loops:
    p=main.matrix_world@main.data.vertices[loop.vertex_index].co
    x=1095+p.x/0.18*164
    y=60+(1.718-p.z)/.273*248
    uv.data[loop.index].uv=(x/1536,1-y/1024)
mat=main.data.materials[0].copy();mat.name='Reference_Suit_Face_Prototype';main.data.materials[0]=mat
n=mat.node_tree.nodes;l=mat.node_tree.links;n.clear()
def node(kind):return n.new(kind)
def mathnode(op,a,b=None):
    m=node('ShaderNodeMath');m.operation=op
    for idx,val in enumerate([a,b] if b is not None else [a]):
        if hasattr(val,'node'):l.new(val,m.inputs[idx])
        else:m.inputs[idx].default_value=val
    return m.outputs[0]
original=next(i for i in bpy.data.images if i.name.endswith('_color.jpg'))
tex=node('ShaderNodeTexImage');tex.image=original
uvorig=node('ShaderNodeUVMap');uvorig.uv_map=main.data.uv_layers[0].name;l.new(uvorig.outputs['UV'],tex.inputs['Vector'])
uvref=node('ShaderNodeUVMap');uvref.uv_map='ReferenceProjection'
face=node('ShaderNodeTexImage');face.image=ref;face.extension='EXTEND';l.new(uvref.outputs['UV'],face.inputs['Vector'])
# Explicit world-aligned object coordinate reference, independent of mesh local axes.
origin=bpy.data.objects.new('ProjectionOrigin',None);bpy.context.collection.objects.link(origin)
coord=node('ShaderNodeTexCoord');coord.object=origin
xyz=node('ShaderNodeSeparateXYZ');l.new(coord.outputs['Object'],xyz.inputs[0]);x,y,z=[xyz.outputs[k] for k in 'XYZ']
absx=mathnode('ABSOLUTE',x)
cloth=mathnode('MULTIPLY',mathnode('LESS_THAN',z,1.447),mathnode('GREATER_THAN',z,.095))
cloth=mathnode('MULTIPLY',cloth,mathnode('LESS_THAN',absx,.625))
bw=node('ShaderNodeRGBToBW');l.new(tex.outputs['Color'],bw.inputs[0])
shade=mathnode('ADD',mathnode('MULTIPLY',bw.outputs[0],.55),.38)
blue=node('ShaderNodeMixRGB');blue.blend_type='MULTIPLY';blue.inputs[0].default_value=1;blue.inputs[1].default_value=(.37,.53,.79,1);l.new(shade,blue.inputs[2])
mix=node('ShaderNodeMixRGB');l.new(cloth,mix.inputs[0]);l.new(tex.outputs['Color'],mix.inputs[1]);l.new(blue.outputs[0],mix.inputs[2])
shirtwidth=mathnode('MULTIPLY',mathnode('MAXIMUM',mathnode('SUBTRACT',z,1.20),0),.30)
shirt=mathnode('MULTIPLY',mathnode('LESS_THAN',absx,shirtwidth),mathnode('GREATER_THAN',z,1.20));shirt=mathnode('MULTIPLY',shirt,mathnode('LESS_THAN',z,1.43))
shirtmix=node('ShaderNodeMixRGB');l.new(shirt,shirtmix.inputs[0]);l.new(mix.outputs[0],shirtmix.inputs[1]);shirtmix.inputs[2].default_value=(.86,.87,.9,1)
facemask=mathnode('MULTIPLY',mathnode('LESS_THAN',y,-.085),mathnode('GREATER_THAN',z,1.485))
facemask=mathnode('MULTIPLY',facemask,mathnode('LESS_THAN',z,1.707))
edge=mathnode('MULTIPLY',mathnode('MAXIMUM',mathnode('SUBTRACT',.084,absx),0),90);edge=mathnode('MINIMUM',edge,1)
facemask=mathnode('MULTIPLY',facemask,edge)
facemix=node('ShaderNodeMixRGB');l.new(facemask,facemix.inputs[0]);l.new(shirtmix.outputs[0],facemix.inputs[1]);l.new(face.outputs['Color'],facemix.inputs[2])
em=node('ShaderNodeEmission');l.new(facemix.outputs[0],em.inputs['Color']);output=node('ShaderNodeOutputMaterial');l.new(em.outputs[0],output.inputs['Surface'])
baked=bpy.data.images.new('CustomAvatar_BaseColor',width=2048,height=2048,alpha=False)
target=node('ShaderNodeTexImage');target.image=baked;n.active=target;target.select=True
main.data.uv_layers.active_index=0
bpy.context.scene.render.engine='CYCLES';bpy.context.scene.cycles.samples=1
bpy.ops.object.select_all(action='DESELECT');main.select_set(True);bpy.context.view_layer.objects.active=main
bpy.context.scene.render.bake.margin=12
bpy.ops.object.bake(type='EMIT')
baked.filepath_raw=str(ASSET/'CustomAvatar_BaseColor.png');baked.file_format='PNG';baked.save();baked.pack()
# Replace the projection graph with portable ordinary UV material for FBX.
n.clear();tex=node('ShaderNodeTexImage');tex.image=baked
bs=node('ShaderNodeBsdfPrincipled');l.new(tex.outputs['Color'],bs.inputs['Base Color']);bs.inputs['Roughness'].default_value=.72
output=node('ShaderNodeOutputMaterial');l.new(bs.outputs[0],output.inputs['Surface'])
# A tied bun is actual geometry, weighted to the existing head bone.
hair=bpy.data.materials.new('Dark_Hair');hair.diffuse_color=(.025,.018,.014,1);hair.use_nodes=True
hair.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(.025,.018,.014,1)
hair.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value=.62
bpy.ops.mesh.primitive_uv_sphere_add(segments=32,ring_count=20,location=(0,.075,1.635),scale=(.065,.052,.063))
bun=bpy.context.object;bun.name='Reference_Hair_Bun';bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
bun.data.materials.append(hair)
group=bun.vertex_groups.new(name='Head');group.add(list(range(len(bun.data.vertices))),1,'REPLACE')
modifier=bun.modifiers.new('Head_Rig','ARMATURE');modifier.object=arm
for poly in bun.data.polygons:poly.use_smooth=True
meshes.append(bun)
# Store useful animation checks; these are engineering tests, not signed phrases.
scene=bpy.context.scene;scene.render.fps=25;scene.frame_start=1;scene.frame_end=60
for side,sign in [('Left',1),('Right',-1)]:
    pb=arm.pose.bones.get(side+'Arm')
    if pb:
        pb.rotation_mode='XYZ'
        for frame,angle in [(1,0),(20,.35*sign),(40,-.25*sign),(60,0)]:
            pb.rotation_euler[1]=angle;pb.keyframe_insert(data_path='rotation_euler',frame=frame,group=pb.name)
    for finger in ['Thumb','Index','Middle','Ring','Pinky']:
        for segment in [1,2,3]:
            pb=arm.pose.bones.get(f'{side}Hand{finger}{segment}')
            if pb:
                pb.rotation_mode='XYZ'
                for frame,angle in [(1,0),(20,.5),(40,.85),(60,0)]:
                    pb.rotation_euler[2]=angle*sign;pb.keyframe_insert(data_path='rotation_euler',frame=frame,group=pb.name)
if arm.animation_data and arm.animation_data.action:arm.animation_data.action.name='Rig_Check_Not_Sign_Language'
scene.frame_set(1)
# Export only the rigged character, preserving base hierarchy and weights.
bpy.ops.object.select_all(action='DESELECT')
for o in meshes+[arm]:o.select_set(True)
bpy.context.view_layer.objects.active=arm
fbx=ASSET/'ReferenceWoman_Prototype.fbx'
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH','ARMATURE'},
    add_leaf_bones=False,path_mode='COPY',embed_textures=True,bake_anim=True,bake_anim_use_all_actions=False,
    bake_anim_use_nla_strips=False,axis_forward='-Z',axis_up='Y')
shutil.copy2(ROOT/'assets/3d/valid/LICENSE',ASSET/'BASE_MODEL_LICENSE.txt')
# Presentation renders are kept separate from exported character objects.
scene.render.engine='CYCLES';scene.cycles.samples=24
scene.render.resolution_x=1000;scene.render.resolution_y=900;scene.render.resolution_percentage=100
scene.world.color=(.2,.2,.2)
def point(obj,at):obj.rotation_euler=(Vector(at)-obj.location).to_track_quat('-Z','Y').to_euler()
for pos,power,size in [((2,-3,3),400,4),((-2,-1,2),250,3),((0,2,3),300,3)]:
    bpy.ops.object.light_add(type='AREA',location=pos);lamp=bpy.context.object;lamp.data.energy=power;lamp.data.shape='DISK';lamp.data.size=size;point(lamp,(0,0,1.2))
bpy.ops.object.camera_add(location=(0,-3.2,1.15));camera=bpy.context.object;camera.data.type='ORTHO';camera.data.ortho_scale=1.95;point(camera,(0,0,.9));scene.camera=camera
scene.view_settings.view_transform='AgX'
bpy.ops.wm.save_as_mainfile(filepath=str(ASSET/'ReferenceWoman_Prototype.blend'))
for name,pos in [('front',(0,-3.2,1.15)),('side',(3.2,0,1.15)),('back',(0,3.2,1.15))]:
    camera.location=pos;point(camera,(0,0,.9));scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
report={'fbx':str(fbx),'blend':str(ASSET/'ReferenceWoman_Prototype.blend'),'mesh_objects':len(meshes),
    'bones':len(arm.data.bones),'vertices':sum(len(o.data.vertices) for o in meshes),
    'method':'MIT VALID rigged base customization with frontal photo projection, clothing recolor and geometric bun; not image-to-3D reconstruction.',
    'limitations':['Face geometry inherited from base; likeness not reconstructed.','Front photo projection has side-view seams.','Suit recolor is approximate, not tailored geometry.','No facial expression rig added.','Animation is rig check, not verified sign language.']}
(OUT/'build-report.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report))
