import os
"""Rebuild hand deformation in a new asset; keep supplied files untouched."""
import bpy,json,math,heapq
import numpy as np
from pathlib import Path
from mathutils import Vector,Quaternion,Matrix
from mathutils.kdtree import KDTree
ROOT=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('SIGNHUMAN_WORK_DIR', str(Path(__file__).resolve().parents[1]/'assets/3d/user/source')));OUT.mkdir(exist_ok=True)
WEB=ROOT/'assets/3d/user';WEB.mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(Path(os.environ.get('SIGNHUMAN_SOURCE_DIR', str(ROOT/'assets/3d/user/source')))/'SignHuman_Final.fbx'))
mesh=next(o for o in bpy.context.scene.objects if o.type=='MESH');arm=mesh.find_armature()
for modifier in mesh.modifiers:
    if modifier.type=='ARMATURE':modifier.use_deform_preserve_volume=False
P=np.array([mesh.matrix_world@v.co for v in mesh.data.vertices],dtype=float)
edges=np.array([e.vertices[:] for e in mesh.data.edges],dtype=int)
base_lengths=np.linalg.norm(P[edges[:,0]]-P[edges[:,1]],axis=1)
fingers=['Thumb','Index','Middle','Ring','Pinky'];sides=['Left','Right']
report={'source':r'C:\Users\admin\Desktop\3D\SignHuman_Final.fbx','before':{},'after':{},'repairs':{}}
region=np.zeros(len(P),dtype=bool)
for side in sides:
    wrist=arm.matrix_world@arm.data.bones[side+'Hand'].head_local
    region|=np.linalg.norm(P-np.array(wrist),axis=1)<.25
edge_mask=region[edges[:,0]]&region[edges[:,1]]&(base_lengths>.0002)
test_edges=edges[edge_mask];test_lengths=base_lengths[edge_mask]

def reset():
    for pb in arm.pose.bones:pb.matrix_basis=Matrix.Identity(4)
    bpy.context.view_layer.update()

def evaluate(label,kind):
    reset()
    for side in sides:
        index=arm.data.bones[side+'HandIndex1'].head_local
        pinky=arm.data.bones[side+'HandPinky1'].head_local
        along=(arm.data.bones[side+'HandMiddle1'].head_local-arm.data.bones[side+'Hand'].head_local).normalized()
        normal=(index-pinky).cross(along).normalized()
        for finger in fingers:
            for j in (1,2,3):
                name=f'{side}Hand{finger}{j}';pb=arm.pose.bones[name]
                direction=(pb.bone.tail_local-pb.bone.head_local).normalized()
                axis=direction.cross(normal).normalized()
                local=pb.bone.matrix_local.to_quaternion().inverted()@axis
                angle=0 if kind=='open' or kind=='point' and finger=='Index' else .65 if kind in ('fist','point') else .4 if kind=='pinch' and finger in ('Thumb','Index') else 0
                pb.rotation_mode='QUATERNION';pb.rotation_quaternion=Quaternion(local,angle)
        if kind=='wrist':arm.pose.bones[side+'Hand'].rotation_quaternion=Quaternion((0,1,0),.7)
    bpy.context.view_layer.update()
    dg=bpy.context.evaluated_depsgraph_get();obj=mesh.evaluated_get(dg);me=obj.to_mesh()
    Q=np.array([obj.matrix_world@v.co for v in me.vertices]);obj.to_mesh_clear()
    ratio=np.linalg.norm(Q[test_edges[:,0]]-Q[test_edges[:,1]],axis=1)/test_lengths
    report[label][kind]={'edge_stretch_p99':round(float(np.percentile(ratio,99)),3),'edges_over_3x':int((ratio>3).sum()),'max_stretch':round(float(ratio.max()),2)}
    if kind in ('fist','pinch'):
        scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.light='STUDIO';scene.display.shading.color_type='SINGLE';scene.display.shading.single_color=(.65,.43,.32)
        scene.display.shading.show_cavity=True
        camera=bpy.data.objects.get('HandAuditCamera')
        if not camera:
            camera=bpy.data.objects.new('HandAuditCamera',bpy.data.cameras.new('HandAuditCamera'));scene.collection.objects.link(camera)
        target=Vector((.51,-.085,.90));camera.location=target+Vector((.35,-.5,.23));camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.type='ORTHO';camera.data.ortho_scale=.245;scene.camera=camera
        scene.render.resolution_x=640;scene.render.resolution_y=640;scene.render.resolution_percentage=100
        scene.render.filepath=str(ROOT/f'outputs/hand-audit/{label}-{kind}.png');bpy.ops.render.render(write_still=True)
for kind in ['open','fist','point','pinch','wrist']:evaluate('before',kind)
reset()

# Place wrist inside the mesh, merge the fourth deform segment into the distal.
bpy.context.view_layer.objects.active=arm;bpy.ops.object.mode_set(mode='EDIT')
for side in sides:
    eb=arm.data.edit_bones;middle=eb[side+'HandMiddle1'].head.copy()
    old=eb[side+'Hand'].head.copy();u=(old-eb[side+'ForeArm'].head).normalized()
    wrist=middle-u*.085
    eb[side+'Hand'].use_connect=False;eb[side+'ForeArm'].tail=wrist;eb[side+'Hand'].head=wrist;eb[side+'Hand'].tail=middle
    normal=(eb[side+'HandIndex1'].head-eb[side+'HandPinky1'].head).cross(middle-wrist).normalized()
    eb[side+'Hand'].align_roll(normal)
    for finger in fingers:
        names=[f'{side}Hand{finger}{j}' for j in (1,2,3,4)]
        start=eb[names[0]].head.copy();tip=eb[names[3]].tail.copy();d=tip-start
        for j in range(3):
            bone=eb[names[j]];bone.use_connect=False
            bone.head=start+d*[0,.45,.75][j];bone.tail=start+d*[.45,.75,1][j];bone.align_roll(normal)
        end=eb[names[3]];end.use_connect=False;end.head=tip;end.tail=tip+d.normalized()*.003;end.use_deform=False
    report['repairs'][side]={'old_wrist':list(old),'new_wrist':list(wrist),'wrist_shift_m':(wrist-old).length}
bpy.ops.object.mode_set(mode='OBJECT')

for side in sides:
    bones=arm.data.bones;wrist=np.array(arm.matrix_world@bones[side+'Hand'].head_local)
    palm=np.array(arm.matrix_world@bones[side+'HandMiddle1'].head_local)
    axis=(palm-wrist);axis/=np.linalg.norm(axis)
    mask=(np.linalg.norm(P-wrist,axis=1)<.24)&(P[:,0]*(1 if side=='Left' else -1)>.25)
    ids=np.where(mask)[0];points=P[ids];N=len(ids)
    names=[side+'ForeArm',side+'Hand']+[f'{side}Hand{f}{j}' for f in fingers for j in (1,2,3)]
    W=np.zeros((N,len(names)),dtype=np.float32)
    # Forearm/palm blend around the newly located wrist.
    t=(points-wrist)@axis;hand=np.clip((t+.025)/.045,0,1);hand=hand*hand*(3-2*hand)
    W[:,0]=1-hand;W[:,1]=hand
    distances=[];parameters=[];lengths=[];tips=[]
    for finger in fingers:
        a=np.array(arm.matrix_world@bones[f'{side}Hand{finger}1'].head_local)
        b=np.array(arm.matrix_world@bones[f'{side}Hand{finger}3'].tail_local)
        d=b-a;length=np.linalg.norm(d);u=d/length
        tips.append(b)
        x=(points-a)@u;closest=a+np.clip(x,0,length)[:,None]*u
        distances.append(np.linalg.norm(points-closest,axis=1));parameters.append(x/length);lengths.append(length)
    D=np.array(distances).T;T=np.array(parameters).T
    lookup=np.full(len(P),-1,dtype=int);lookup[ids]=np.arange(N)
    E=lookup[edges];E=E[(E[:,0]>=0)&(E[:,1]>=0)]
    adjacency=[[] for _ in range(N)]
    for a,b in E:
        cost=float(np.linalg.norm(points[a]-points[b]));adjacency[a].append((b,cost));adjacency[b].append((a,cost))
    geodesic=[]
    for tip in tips:
        distances_to_tip=np.linalg.norm(points-tip,axis=1);seeds=np.argsort(distances_to_tip)[:5]
        dist=np.full(N,np.inf);heap=[]
        for seed in seeds:dist[seed]=0;heapq.heappush(heap,(0,int(seed)))
        while heap:
            cost,index=heapq.heappop(heap)
            if cost>dist[index]+1e-10:continue
            for neighbor,length in adjacency[index]:
                new=cost+length
                if new<dist[neighbor]:dist[neighbor]=new;heapq.heappush(heap,(new,int(neighbor)))
        geodesic.append(dist)
    G=np.array(geodesic).T;choice=G.argmin(axis=1)
    disconnected=~np.isfinite(G.min(axis=1));choice[disconnected]=D[disconnected].argmin(axis=1)
    # The supplied PCA bones cross neighboring fingers. Follow each finger's
    # mesh-connected centerline instead of fitting one straight line to a fan.
    curves=[]
    curve_stats={}
    for f,finger in enumerate(fingers):
        curve=[];belongs=choice==f;length=lengths[f]
        for distance in [length*.95,length*.55,length*.25,.003]:
            candidates=np.where(belongs & np.isfinite(G[:,f]))[0]
            closest=candidates[np.argsort(np.abs(G[candidates,f]-distance))[:100]]
            curve.append(np.median(points[closest],axis=0))
        segments=[np.linalg.norm(curve[j+1]-curve[j]) for j in range(3)]
        valid=bool(min(segments)>.005 and np.linalg.norm(curve[3]-curve[0])>length*.5)
        curve_stats[finger]={'finite_vertices':int(np.isfinite(G[:,f]).sum()),'centerline_used':valid}
        if not valid:
            curve=[np.array(arm.matrix_world@bones[f'{side}Hand{finger}{j}'].head_local) for j in (1,2,3)]+[tips[f]]
        curves.append(curve)
    report['repairs'][side]['centerline']=curve_stats
    local_normal=(bones[side+'HandIndex1'].head_local-bones[side+'HandPinky1'].head_local).cross(bones[side+'HandMiddle1'].head_local-bones[side+'Hand'].head_local).normalized()
    bpy.context.view_layer.objects.active=arm;bpy.ops.object.mode_set(mode='EDIT');eb=arm.data.edit_bones
    inverse=arm.matrix_world.inverted()
    for f,finger in enumerate(fingers):
        for j in range(3):
            bone=eb[f'{side}Hand{finger}{j+1}'];bone.head=inverse@Vector(curves[f][j]);bone.tail=inverse@Vector(curves[f][j+1])
            bone.align_roll(local_normal)
        end=eb[f'{side}Hand{finger}4'];end.head=inverse@Vector(curves[f][3]);end.tail=end.head+(eb[f'{side}Hand{finger}3'].tail-eb[f'{side}Hand{finger}3'].head).normalized()*.003
    eb[side+'Hand'].tail=inverse@Vector(curves[2][0])
    bpy.ops.object.mode_set(mode='OBJECT')
    D=np.full((N,5),np.inf);T=np.zeros((N,5))
    for f,curve in enumerate(curves):
        total=sum(np.linalg.norm(curve[j+1]-curve[j]) for j in range(3));offset=0
        for j in range(3):
            a,b=curve[j],curve[j+1];d=b-a;length=np.linalg.norm(d);u=d/length
            along=(points-a)@u;clamped=np.clip(along,0,length)
            dist=np.linalg.norm(points-(a+clamped[:,None]*u),axis=1);closer=dist<D[:,f]
            D[closer,f]=dist[closer];T[closer,f]=(offset+along[closer])/total
            offset+=length
    for i in range(N):
        f=int(choice[i]);along=float(T[i,f]);distance=float(D[i,f])
        if along<=-.02 or distance>.032:continue
        # Never bind palm or forearm to a remote fingertip. Feather finger roots.
        blend=np.clip(along/.20,0,1)*hand[i]
        blend=blend*blend*(3-2*blend)
        if blend<.001:continue
        # Two adjacent joints blend smoothly along each phalanx.
        centres=[.225,.60,.875];pos=along
        weights=np.maximum(0,1-np.abs(np.array(centres)-pos)/.34)
        if not weights.any():weights[np.argmin(np.abs(np.array(centres)-pos))]=1
        weights/=weights.sum();W[i,:2]*=1-blend;W[i,2+f*3:5+f*3]=weights*blend
    # Smooth over mesh adjacency, not Euclidean neighbors across separate fingers.
    degree=np.bincount(E.ravel(),minlength=N).astype(np.float32);degree=np.maximum(degree,1)
    for _ in range(30):
        sums=np.zeros_like(W);np.add.at(sums,E[:,0],W[E[:,1]]);np.add.at(sums,E[:,1],W[E[:,0]])
        W=.55*W+.45*sums/degree[:,None]
    for name in names:
        if name not in mesh.vertex_groups:mesh.vertex_groups.new(name=name)
    for group in mesh.vertex_groups:group.remove(ids.tolist())
    for i,index in enumerate(ids):
        chosen=np.argsort(W[i])[-4:];total=float(W[i,chosen].sum())
        for k in chosen:
            weight=float(W[i,k])/total
            if weight>.0001:mesh.vertex_groups[names[k]].add([int(index)],weight,'REPLACE')
    report['repairs'][side]['reweighted_vertices']=N

# Other unweighted source vertices receive nearest valid weights.
deform={g.index for g in mesh.vertex_groups if g.name in arm.data.bones and arm.data.bones[g.name].use_deform}
zero=[v.index for v in mesh.data.vertices if sum(g.weight for g in v.groups if g.group in deform)<.001]
bad=set(zero);tree=KDTree(len(P)-len(zero))
for v in mesh.data.vertices:
    if v.index not in bad:tree.insert(v.co,v.index)
tree.balance()
for index in zero:
    _,near,_=tree.find(mesh.data.vertices[index].co)
    weights=sorted([(g.group,g.weight) for g in mesh.data.vertices[near].groups if g.group in deform],key=lambda x:-x[1])[:4]
    total=sum(w for _,w in weights)
    for group,w in weights:mesh.vertex_groups[group].add([index],w/total,'REPLACE')
report['repairs']['other_unweighted']=len(zero)
for kind in ['open','fist','point','pinch','wrist']:evaluate('after',kind)
reset()
for image in bpy.data.images:
    if max(image.size)>2048:image.scale(2048,2048)
for obj in list(bpy.context.scene.objects):
    if obj.type in ('LIGHT','CAMERA'):bpy.data.objects.remove(obj,do_unlink=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'SignHuman_HandsOptimized.blend'))
bpy.ops.export_scene.fbx(filepath=str(OUT/'SignHuman_HandsOptimized.fbx'),object_types={'ARMATURE','MESH'},add_leaf_bones=False,bake_anim=False,path_mode='COPY',embed_textures=True)
pending=WEB/'SignHuman_HandsOptimized.next.glb'
bpy.ops.export_scene.gltf(filepath=str(pending),export_format='GLB',export_animations=False)
pending.replace(WEB/'SignHuman_HandsOptimized.glb')
(OUT/'hand-repair-report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
(ROOT/'outputs/hand-audit/repair-report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('HAND_REPAIR',json.dumps(report))
