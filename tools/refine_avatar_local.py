"""Local V3 geometry refinement. No cloud calls or identity reconstruction claim."""
import bpy,bmesh,math,json,shutil
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]
ASSET=ROOT/'assets/3d/custom-v3';OUT=ROOT/'outputs/reference-v3'
ASSET.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'assets/3d/custom-v2/ReferenceWoman_Aligned.blend'))
arm=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
for pb in arm.pose.bones:pb.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update()
main=bpy.data.objects['H_DDS_HighRes']
# Conform independent garment pieces to the actual torso surface rather than
# leaving planar strips floating in front of the body.
vertices=[main.matrix_world@v.co for v in main.data.vertices]
polygons=[list(p.vertices) for p in main.data.polygons]
bvh=BVHTree.FromPolygons(vertices,polygons)
garment_stats=[]
for obj in list(bpy.context.scene.objects):
    if obj.name.startswith(('Notched_Lapel','Pocket_Flap')):
        for modifier in list(obj.modifiers):
            if modifier.type!='ARMATURE':obj.modifiers.remove(modifier)
        bm=bmesh.new();bm.from_mesh(obj.data)
        bmesh.ops.triangulate(bm,faces=list(bm.faces))
        bmesh.ops.subdivide_edges(bm,edges=list(bm.edges),cuts=3,use_grid_fill=True)
        bm.to_mesh(obj.data);bm.free()
        inverse=obj.matrix_world.inverted();max_gap=0
        for v in obj.data.vertices:
            world=obj.matrix_world@v.co
            hit,normal,index,distance=bvh.ray_cast(Vector((world.x,-1,world.z)),Vector((0,1,0)),2)
            if hit is not None:
                max_gap=max(max_gap,abs(world.y-hit.y));world.y=hit.y-.0025;v.co=inverse@world
        obj.vertex_groups.clear();vg=obj.vertex_groups.new(name='Spine2');vg.add(list(range(len(obj.data.vertices))),1,'REPLACE')
        solid=obj.modifiers.new('TailoringThickness','SOLIDIFY');solid.thickness=.0013
        for p in obj.data.polygons:p.use_smooth=True
        garment_stats.append({'name':obj.name,'vertices':len(obj.data.vertices),'old_max_gap_m':max_gap})
# Small silhouette correction to the trouser calves; fingers are unchanged.
inverse=main.matrix_world.inverted()
for v in main.data.vertices:
    p=main.matrix_world@v.co
    if .09<p.z<.63:
        center=.083 if p.x>0 else -.083
        strength=.09*math.sin(math.pi*(p.z-.09)/.54)
        p.x=center+(p.x-center)*(1+strength);v.co=inverse@p
# Smooth the existing facial/body surface while retaining all skin weights.
sub=main.modifiers.new('SurfaceRefinement','SUBSURF');sub.levels=1;sub.render_levels=1
sub.subdivision_type='CATMULL_CLARK'
# Replace the spherical bun with scalp geometry and coiled strand geometry.
old=bpy.data.objects.get('Reference_Hair_Bun')
if old:bpy.data.objects.remove(old,do_unlink=True)
hair=bpy.data.materials.new('Local_DarkBrown_Hair');hair.use_nodes=True
principled=hair.node_tree.nodes.get('Principled BSDF')
principled.inputs['Base Color'].default_value=(.016,.010,.007,1)
principled.inputs['Roughness'].default_value=.58
def bind(obj):
    vg=obj.vertex_groups.new(name='Head');vg.add(list(range(len(obj.data.vertices))),1,'REPLACE')
    mod=obj.modifiers.new('HeadSkinning','ARMATURE');mod.object=arm
    obj.data.materials.append(hair)
    for p in obj.data.polygons:p.use_smooth=True
def scalp_point(phi,t,extra=0):
    front=max(0,-math.sin(phi));back=max(0,math.sin(phi))
    limit=1.65-.66*front+.62*back
    theta=t*limit
    return Vector(((.077+extra)*math.sin(theta)*math.cos(phi),
                   -.018+(.084+extra)*math.sin(theta)*math.sin(phi),
                   1.562+(.090+extra)*math.cos(theta)))
verts=[];faces=[];around=96;rings=25
for j in range(rings):
    for i in range(around):verts.append(scalp_point(2*math.pi*i/around,.015+.985*j/(rings-1)))
for j in range(rings-1):
    for i in range(around):
        a=j*around+i;b=j*around+(i+1)%around;faces.append((a,b,b+around,a+around))
mesh=bpy.data.meshes.new('Fitted_Scalp');mesh.from_pydata(verts,[],faces);mesh.update()
cap=bpy.data.objects.new('Fitted_Scalp',mesh);bpy.context.collection.objects.link(cap);bind(cap)
def strand(name,points,radius):
    curve=bpy.data.curves.new(name,'CURVE');curve.dimensions='3D';curve.resolution_u=2
    curve.bevel_depth=radius;curve.bevel_resolution=2
    spline=curve.splines.new('POLY');spline.points.add(len(points)-1)
    for p,co in zip(spline.points,points):p.co=(*co,1)
    obj=bpy.data.objects.new(name,curve);bpy.context.collection.objects.link(obj)
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    bpy.ops.object.convert(target='MESH');bind(bpy.context.object)
for i in range(80):
    phi=2*math.pi*i/80
    strand('Scalp_Strand_%02d'%i,[scalp_point(phi,.12+.88*j/22,.0008) for j in range(23)],.00042)
for i in range(15):
    points=[]
    for j in range(100):
        a=2*math.pi*j/99;radius=.021+.012*math.sin(a*2+i*.4)
        phase=2*math.pi*i/15
        points.append(Vector(((radius+.010)*math.cos(a+phase),.090+.012*math.sin(a*3+phase),1.566+.038*math.sin(a+phase))))
    strand('Coiled_Bun_%02d'%i,points,.0034)
# Merge strands into one skinned mesh to avoid dozens of browser draw calls.
bpy.ops.object.select_all(action='DESELECT')
hair_objects=[o for o in bpy.context.scene.objects if o.type=='MESH' and (o.name=='Fitted_Scalp' or o.name.startswith(('Scalp_Strand_','Coiled_Bun_')))]
for obj in hair_objects:obj.select_set(True)
bpy.context.view_layer.objects.active=cap;bpy.ops.object.join();cap.name='Skinned_Scalp_And_Bun'
# Preserve a clean T-pose bind FBX. The saved Blender scene presents A-pose.
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
bpy.ops.object.select_all(action='DESELECT')
for obj in meshes+[arm]:obj.select_set(True)
bpy.context.view_layer.objects.active=arm
fbx=ASSET/'ReferenceWoman_LocalRefined.fbx'
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'ARMATURE','MESH'},
    add_leaf_bones=False,path_mode='COPY',embed_textures=True,bake_anim=False,axis_forward='-Z',axis_up='Y')
shutil.copy2(ROOT/'assets/3d/custom-v2/BASE_MODEL_LICENSE.txt',ASSET/'BASE_MODEL_LICENSE.txt')
for image in bpy.data.images:
    if image.name=='CustomAvatar_BaseColor':
        image.filepath_raw=str(ASSET/'CustomAvatar_BaseColor.png');image.file_format='PNG';image.save();image.pack()
for side,sign in [('Left',1),('Right',-1)]:
    pb=arm.pose.bones.get(side+'Arm');child=arm.pose.bones.get(side+'ForeArm')
    direction=(child.head-pb.head).normalized();target=arm.matrix_world.inverted().to_3x3()@Vector((sign*.52,0,-.85))
    q=direction.rotation_difference(target.normalized());pivot=pb.head.copy()
    pb.matrix=Matrix.Translation(pivot)@q.to_matrix().to_4x4()@Matrix.Translation(-pivot)@pb.matrix
    bpy.context.view_layer.update()
scene=bpy.context.scene;camera=scene.camera
camera.data.ortho_scale=2.05
scene.cycles.samples=32;scene.render.resolution_x=1000;scene.render.resolution_y=1000
def aim(pos,target):camera.location=pos;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler()
aim((0,-3,.9),(0,0,.825))
bpy.ops.wm.save_as_mainfile(filepath=str(ASSET/'ReferenceWoman_LocalRefined.blend'))
for name,pos in [('front',(0,-3,.9)),('side',(3,0,.9)),('back',(0,3,.9))]:
    aim(pos,(0,0,.825));scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
camera.data.ortho_scale=.42;aim((0,-2,1.56),(0,-.03,1.56));scene.render.filepath=str(OUT/'head-closeup.png');bpy.ops.render.render(write_still=True)
report={'stage':'local geometry refinement, not high-fidelity completion','bones':len(arm.data.bones),
    'garment_fit':garment_stats,'hair_mesh_objects':1,'hair_strand_groups':95,'cloud_used':False,
    'limitations':['Identity geometry still relies on template mesh and V2 photo textures.','Hair is procedural strand geometry, not scanned hair.','Lapel and clothing deformation still needs pose checks.','Not a high-fidelity likeness or verified sign-language model.']}
(OUT/'report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
