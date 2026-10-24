import os
"""Use the existing VRM's clean hand topology/weights on the user's body."""
import bpy,bmesh,json,struct,math
import numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[1];OUT=Path(os.environ.get('SIGNHUMAN_WORK_DIR', str(Path(__file__).resolve().parents[1]/'assets/3d/user/source')))
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(OUT/'SignHuman_HandsOptimized.fbx'))
body=next(o for o in bpy.context.scene.objects if o.type=='MESH');target=body.find_armature();original_objects=set(bpy.data.objects)
raw=(ROOT/'assets/3d/sample.vrm').read_bytes();length,_=struct.unpack_from('<II',raw,12);metadata=json.loads(raw[20:20+length])
mapping={k:metadata['nodes'][v['node']]['name'] for k,v in metadata['extensions']['VRMC_vrm']['humanoid']['humanBones'].items()}
bpy.ops.import_scene.gltf(filepath=str(ROOT/'assets/3d/sample.vrm'))
donor_objects=set(bpy.data.objects)-original_objects;donor_arm=next(o for o in donor_objects if o.type=='ARMATURE');donor=next(o for o in donor_objects if o.type=='MESH' and o.name.startswith('Body'))
report={'source':'existing sample.vrm hands + supplied user body','hands':{}}
fingers=['Thumb','Index','Middle','Ring','Little']
skin=bpy.data.materials.new('HandSkin');skin.diffuse_color=(1,1,1,1);skin.use_nodes=True
color_node=skin.node_tree.nodes.new('ShaderNodeVertexColor');color_node.layer_name='HandTint'
skin.node_tree.links.new(color_node.outputs['Color'],skin.node_tree.nodes.get('Principled BSDF').inputs['Base Color'])
skin.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value=.65

def world_head(arm,name):return arm.matrix_world@arm.data.bones[name].head_local
def basis(along,across):
    y=along.normalized();x=(across-y*across.dot(y)).normalized();z=x.cross(y).normalized()
    return Matrix((x,y,z)).transposed()

for side,lower in [('Left','left'),('Right','right')]:
    sign=1 if side=='Left' else -1
    wrist=world_head(target,side+'Hand');elbow=world_head(target,side+'ForeArm');along=(wrist-elbow).normalized()
    cut=wrist-along*.025
    # Cut the faulty source hands off at a forearm cross-section.
    bm=bmesh.new();bm.from_mesh(body.data)
    selected=[v for v in bm.verts if (body.matrix_world@v.co).x*sign>.30]
    subset=set(selected);geom=selected+[e for e in bm.edges if all(v in subset for v in e.verts)]+[f for f in bm.faces if all(v in subset for v in f.verts)]
    local_cut=body.matrix_world.inverted()@cut;local_normal=body.matrix_world.to_3x3().transposed()@along
    bmesh.ops.bisect_plane(bm,geom=geom,dist=.000001,plane_co=local_cut,plane_no=local_normal,clear_outer=True)
    ring=[body.matrix_world@v.co for v in bm.verts if (body.matrix_world@v.co).x*sign>.30 and abs(((body.matrix_world@v.co)-cut).dot(along))<.00005]
    if len(ring)<8:raise ValueError('Body wrist boundary could not be found')
    centre=sum(ring,Vector())/len(ring);wrist=centre+along*.025
    bm.to_mesh(body.data);bm.free();body.data.update()
    # Both sides of the wrist seam must follow the forearm, not different bones.
    forearm_group=body.vertex_groups.get(side+'ForeArm') or body.vertex_groups.new(name=side+'ForeArm')
    for vertex in body.data.vertices:
        world=body.matrix_world@vertex.co;depth=(world-cut).dot(along)
        if world.x*sign>.30 and -.035<depth<.0001:
            blend=max(0,min(1,(depth+.035)/.025));existing={g.group:g.weight for g in vertex.groups}
            for g in list(vertex.groups):g.weight*=1-blend
            forearm_group.add([vertex.index],existing.get(forearm_group.index,0)*(1-blend)+blend,'REPLACE')
    dw=world_head(donor_arm,mapping[lower+'Hand']);dm=world_head(donor_arm,mapping[lower+'MiddleProximal'])
    di=world_head(donor_arm,mapping[lower+'IndexProximal']);dp=world_head(donor_arm,mapping[lower+'LittleProximal'])
    donor_basis=basis(dm-dw,di-dp);target_basis=basis(along,Vector((0,-1,0)))
    rotation=target_basis@donor_basis.inverted();scale=1.05
    transform=Matrix.Translation(wrist)@rotation.to_4x4()@Matrix.Scale(scale,4)@Matrix.Translation(-dw)
    rename={mapping[lower+'Hand']:side+'Hand',mapping[lower+'LowerArm']:side+'ForeArm','J_Roll_'+side[0]+'_Hand':side+'ForeArm'}
    for finger in fingers:
        parts=['Metacarpal','Proximal','Distal'] if finger=='Thumb' else ['Proximal','Intermediate','Distal']
        for j,part in enumerate(parts,1):rename[mapping[lower+finger+part]]=side+'Hand'+('Pinky' if finger=='Little' else finger)+str(j)
    # Duplicate the donor's bind matrices, including its local axes, exactly.
    bpy.context.view_layer.objects.active=target;bpy.ops.object.mode_set(mode='EDIT');eb=target.data.edit_bones
    for source,name in rename.items():
        if source not in donor_arm.data.bones or name==side+'ForeArm':continue
        bone=eb[name];bone.use_connect=False
        matrix=target.matrix_world.inverted()@transform@donor_arm.matrix_world@donor_arm.data.bones[source].matrix_local
        location=matrix.translation;rotation_part=matrix.to_quaternion().to_matrix().to_4x4();rotation_part.translation=location
        bone.matrix=rotation_part;bone.length=max(.003,donor_arm.data.bones[source].length*scale);bone.use_deform=True
    eb[side+'ForeArm'].tail=target.matrix_world.inverted()@wrist
    # Distal end references must follow the true preceding phalanx direction.
    for finger in fingers:
        name=side+'Hand'+('Pinky' if finger=='Little' else finger)
        d=eb[name+'3'].head-eb[name+'2'].head
        eb[name+'3'].tail=eb[name+'3'].head+d*.75
        end=eb[name+'4'];end.use_connect=False;end.head=eb[name+'3'].tail;end.tail=end.head+d.normalized()*.003;end.use_deform=False
    bpy.ops.object.mode_set(mode='OBJECT')
    # Extract a little forearm together with the donor hand. Keep all weights.
    donor_along=(dm-dw).normalized();keep=[v.index for v in donor.data.vertices if ((donor.matrix_world@v.co)-dw).dot(donor_along)>-.07 and (donor.matrix_world@v.co).x*sign>.35]
    lookup={i:j for j,i in enumerate(keep)};faces=[tuple(lookup[i] for i in p.vertices) for p in donor.data.polygons if all(i in lookup for i in p.vertices)]
    data=bpy.data.meshes.new(side+'CleanHand');data.from_pydata([transform@(donor.matrix_world@donor.data.vertices[i].co) for i in keep],[],faces);data.update()
    obj=bpy.data.objects.new(side+'CleanHand',data);bpy.context.collection.objects.link(obj);obj.data.materials.append(skin)
    obj.parent=target;obj.matrix_parent_inverse=target.matrix_world.inverted();obj.matrix_world=Matrix.Identity(4)
    for name in set(rename.values()):obj.vertex_groups.new(name=name)
    for j,i in enumerate(keep):
        weights={}
        for g in donor.data.vertices[i].groups:
            name=rename.get(donor.vertex_groups[g.group].name,side+'ForeArm');weights[name]=weights.get(name,0)+g.weight
        total=sum(weights.values())
        if total==0:weights={side+'ForeArm':1};total=1
        for name,w in weights.items():obj.vertex_groups[name].add([j],w/total,'REPLACE')
    bm=bmesh.new();bm.from_mesh(data)
    bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.000001,plane_co=centre,plane_no=along,clear_inner=True)
    # Match the open wrist boundary; feather over 25mm toward the donor shape.
    x=target_basis.col[0];z=target_basis.col[2]
    angles=[math.atan2((p-centre).dot(z),(p-centre).dot(x)) for p in ring]
    for v in bm.verts:
        depth=(v.co-centre).dot(along)
        if depth<.025:
            angle=math.atan2((v.co-centre).dot(z),(v.co-centre).dot(x));at=min(range(len(ring)),key=lambda k:abs(math.atan2(math.sin(angles[k]-angle),math.cos(angles[k]-angle))))
            radial=v.co-centre-along*depth;target_radial=ring[at]-centre
            v.co+= (target_radial-radial)*max(0,1-depth/.025)
    bm.to_mesh(data);bm.free();data.update()
    tint=data.color_attributes.new(name='HandTint',type='FLOAT_COLOR',domain='CORNER')
    for loop in data.loops:
        depth=(data.vertices[loop.vertex_index].co-centre).dot(along);t=max(0,min(1,depth/.06));factor=.65+.35*t*t*(3-2*t)
        tint.data[loop.index].color=(.65*factor,.43*factor,.33*factor,1)
    for polygon in data.polygons:polygon.use_smooth=True
    mod=obj.modifiers.new('CleanHandSkin','ARMATURE');mod.object=target
    conversion=Matrix(((1,0,0),(0,0,1),(0,-1,0)))
    inverse_rotation=(conversion@rotation@conversion.inverted()).inverted().to_quaternion()
    report['hands'][side]={'vertices':len(data.vertices),'polygons':len(data.polygons),'wrist_boundary_vertices':len(ring),'wrist':list(wrist),'inverse_rotation':[inverse_rotation.x,inverse_rotation.y,inverse_rotation.z,inverse_rotation.w]}

for obj in donor_objects:
    if obj.name in bpy.data.objects:bpy.data.objects.remove(obj,do_unlink=True)
for image in bpy.data.images:
    if max(image.size)>2048:image.scale(2048,2048)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'SignHuman_CleanHands.blend'))
bpy.ops.export_scene.fbx(filepath=str(OUT/'SignHuman_CleanHands.fbx'),object_types={'ARMATURE','MESH'},bake_anim=False,add_leaf_bones=False,path_mode='COPY',embed_textures=True)
pending=ROOT/'assets/3d/user/SignHuman_CleanHands.next.glb'
bpy.ops.export_scene.gltf(filepath=str(pending),export_format='GLB',export_animations=False)
pending.replace(pending.with_name('SignHuman_CleanHands.glb'))
(OUT/'clean-hands-report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
(ROOT/'assets/3d/user/standard-hand-alignment.json').write_text(json.dumps(report),encoding='utf8')
print('CLEAN_HANDS',json.dumps(report))
