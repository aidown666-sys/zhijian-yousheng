import * as THREE from 'three';
import {GLTFLoader} from './vendor/examples/jsm/loaders/GLTFLoader.js';
import {VRMLoaderPlugin,VRMUtils} from './vendor/lib/three-vrm.module.js';
import {FBXLoader} from './vendor/examples/jsm/loaders/FBXLoader.js';

const canvas=document.querySelector('#avatar');
const renderer=new THREE.WebGLRenderer({canvas,alpha:true,antialias:true});
renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.outputColorSpace=THREE.SRGBColorSpace;
const scene=new THREE.Scene();
const camera=new THREE.PerspectiveCamera(29,1,.1,30);camera.position.set(0,1.25,2.3);camera.lookAt(0,1.2,0);
scene.add(new THREE.HemisphereLight(0xffffff,0x9daacb,.85));
const light=new THREE.DirectionalLight(0xfff3e2,.9);light.position.set(1,2,3);scene.add(light);
const fill=new THREE.DirectionalLight(0xc7e3ff,.35);fill.position.set(-2,1,1);scene.add(fill);
let vrm,current=null,loadError=null;
let loadVersion=0,isFBX=false;
let userView=null;
function fitView(){if(!userView){camera.position.set(0,1.25,2.3);camera.lookAt(0,1.2,0);return}const tangent=Math.tan(THREE.MathUtils.degToRad(camera.fov/2));const distance=Math.max(userView.height/(2*tangent),userView.width/(2*tangent*camera.aspect))*1.18;camera.position.set(0,userView.center,distance);camera.lookAt(0,userView.center,0)}
let directions=new Map();const temp=new THREE.Vector3();
const palmBases=new Map(),smoothRotations=new Map();
let referenceRig=null,referenceDirections=new Map(),referenceOffsets=new Map();
const referenceNames=[];for(const side of ['left','right']){referenceNames.push(side+'Hand');for(const finger of ['Thumb','Index','Middle','Ring','Little'])for(const part of finger==='Thumb'?['Metacarpal','Proximal','Distal']:['Proximal','Intermediate','Distal'])referenceNames.push(side+finger+part)}
function initializeReference(version,targetRig,targetBind){
 Promise.all([fetch('/assets/3d/user/standard-hand-alignment.json').then(r=>r.json()),new Promise((resolve,reject)=>loader.load('/assets/3d/sample.vrm',g=>resolve(g.userData.vrm),undefined,reject))]).then(([alignment,proxy])=>{
  if(version!==loadVersion){releaseRig(proxy);return}proxy.humanoid.resetNormalizedPose();proxy.update(0);proxy.scene.updateMatrixWorld(true);
  referenceOffsets.clear();for(const name of referenceNames){const source=proxy.humanoid.getRawBoneNode(name),bind=targetBind.get(name);if(!source||!bind)continue;const inverseRotation=new THREE.Quaternion().fromArray(alignment.hands[name.startsWith('left')?'Left':'Right'].inverse_rotation);referenceOffsets.set(name,source.getWorldQuaternion(new THREE.Quaternion()).invert().multiply(inverseRotation).multiply(bind))}
  const savedRig=vrm,savedDirections=directions;vrm=proxy;directions=new Map();
  for(const [a,b] of pairs)saveDirection(a,b);
  for(const side of ['left','right']){saveDirection(side+'Hand',side+'MiddleProximal');for(const finger of ['Thumb','Index','Middle','Ring','Little']){const seg=finger==='Thumb'?['Metacarpal','Proximal','Distal']:['Proximal','Intermediate','Distal'];saveDirection(side+finger+seg[0],side+finger+seg[1]);saveDirection(side+finger+seg[1],side+finger+seg[2]);directions.set(side+finger+seg[2],directions.get(side+finger+seg[1])?.clone()||new THREE.Vector3(side==='left'?1:-1,0,0))}}
  referenceDirections=directions;directions=savedDirections;vrm=savedRig;referenceRig=proxy;window.avatar3dReady=true;
 }).catch(e=>{document.querySelector('#status').textContent='标准手势参考加载失败：'+e.message});
}
function applyReference(frame,dt){
 if(!referenceRig)return;const targetRig=vrm,targetDirections=directions,fbx=isFBX;
 vrm=referenceRig;directions=referenceDirections;isFBX=false;pose(frame);referenceRig.update(dt);referenceRig.scene.updateMatrixWorld(true);vrm=targetRig;directions=targetDirections;isFBX=fbx;
 for(const name of referenceNames){const target=bone(name),source=referenceRig.humanoid.getRawBoneNode(name),offset=referenceOffsets.get(name);if(!target||!source||!offset)continue;const desired=source.getWorldQuaternion(new THREE.Quaternion()).multiply(offset);target.quaternion.copy(target.parent.getWorldQuaternion(new THREE.Quaternion()).invert()).multiply(desired);target.updateWorldMatrix(false,true)}
}
function palmBasis(along,across){const y=along.clone().normalize(),x=across.clone().addScaledVector(y,-across.dot(y));if(x.lengthSq()<1e-8||y.lengthSq()<1e-8)return null;x.normalize();const z=new THREE.Vector3().crossVectors(x,y).normalize();return new THREE.Quaternion().setFromRotationMatrix(new THREE.Matrix4().makeBasis(x,y,z))}
function rememberPalm(side){const wrist=bone(side+'Hand'),mid=bone(side+'MiddleProximal'),index=bone(side+'IndexProximal'),little=bone(side+'LittleProximal');if(!wrist||!mid||!index||!little)return;const inv=wrist.getWorldQuaternion(new THREE.Quaternion()).invert(),position=wrist.getWorldPosition(new THREE.Vector3());const q=palmBasis(mid.getWorldPosition(new THREE.Vector3()).sub(position).applyQuaternion(inv),index.getWorldPosition(new THREE.Vector3()).sub(little.getWorldPosition(new THREE.Vector3())).applyQuaternion(inv));if(q)palmBases.set(side,q)}
function orientPalm(side,hand){const wrist=bone(side+'Hand'),local=palmBases.get(side);if(!wrist||!local)return;const point=i=>new THREE.Vector3(...hand[i]);const world=palmBasis(point(9).sub(point(0)),point(5).sub(point(17)));if(!world)return;wrist.quaternion.copy(wrist.parent.getWorldQuaternion(new THREE.Quaternion()).invert()).multiply(world).multiply(local.clone().invert());wrist.updateWorldMatrix(false,true)}
const pairs=[['rightUpperArm','rightLowerArm',2,3],['rightLowerArm','rightHand',3,4],['leftUpperArm','leftLowerArm',5,6],['leftLowerArm','leftHand',6,7]];
function bone(name){return vrm.humanoid.getNormalizedBoneNode(name)}
function saveDirection(name,next){const a=bone(name),b=bone(next);if(a&&b){const d=b.getWorldPosition(new THREE.Vector3()).sub(a.getWorldPosition(new THREE.Vector3()));d.applyQuaternion(a.getWorldQuaternion(new THREE.Quaternion()).invert()).normalize();directions.set(name,d)}}
const loader=new GLTFLoader();loader.register(parser=>new VRMLoaderPlugin(parser));
function loadVRM(version){loader.load('/assets/3d/sample.vrm',gltf=>{if(version!==loadVersion)return;vrm=gltf.userData.vrm;isFBX=false;VRMUtils.removeUnnecessaryVertices(gltf.scene);
  vrm.scene.traverse(object=>{if(object.isMesh){for(const material of Array.isArray(object.material)?object.material:[object.material]){if(material.name.includes('Tops_01_CLOTH')){material.color?.set('#477bd1');material.shadeColorFactor?.set('#31568e')}}}});
  scene.add(vrm.scene);vrm.scene.updateMatrixWorld(true);
  for(const [a,b] of pairs)saveDirection(a,b);
  for(const side of ['left','right']){saveDirection(side+'Hand',side+'MiddleProximal');
    for(const finger of ['Thumb','Index','Middle','Ring','Little']){const segments=finger==='Thumb'?['Metacarpal','Proximal','Distal']:['Proximal','Intermediate','Distal'];
      saveDirection(side+finger+segments[0],side+finger+segments[1]);saveDirection(side+finger+segments[1],side+finger+segments[2]);
      directions.set(side+finger+segments[2],directions.get(side+finger+segments[1])?.clone()||new THREE.Vector3(side==='left'?1:-1,0,0));}}
  vrm.expressionManager?.setValue('happy',.18);window.avatar3dReady=true;
},undefined,failed);}
function failed(error){loadError=error;document.querySelector('#status').textContent='3D 模型加载失败：'+error.message;console.error(error)}
function releaseRig(rig){rig?.scene.traverse(n=>{if(n.isMesh){n.geometry?.dispose();for(const m of Array.isArray(n.material)?n.material:[n.material]){for(const v of Object.values(m))if(v?.isTexture)v.dispose();m.dispose()}}})}
function disposeModel(){releaseRig(referenceRig);referenceRig=null;referenceDirections.clear();referenceOffsets.clear();if(!vrm)return;scene.remove(vrm.scene);releaseRig(vrm);vrm=null;directions.clear();palmBases.clear();smoothRotations.clear()}
const models=[['SignHuman_Final','我的数字人 · 标准手部版'],['SignHuman_HandsOptimized','我的数字人 · 原手网格修复版（对照）'],['sample','动漫女性（原版）'],['ReferenceWoman_LocalRefined','参考图女性 · 本地细化版'],['ReferenceWoman_Aligned','参考图女性 · 对齐修订版'],['ReferenceWoman_Prototype','参考图女性 · 旧版原型'],['Asian_F_1_Busi','亚洲女性 A · 商务装'],['Asian_F_2_Casual','亚洲女性 B · 休闲装'],['Asian_M_1_Busi','亚洲男性 A · 商务装'],['Asian_M_2_Casual','亚洲男性 B · 休闲装']];
const selector=document.createElement('select');selector.id='character';selector.setAttribute('aria-label','人物形象');
for(const [id,label] of models){const o=document.createElement('option');o.value=id;o.textContent=label;selector.append(o)}
const label=document.createElement('label');label.textContent='人物形象（3D 骨骼模型）';label.append(selector);document.querySelector('section').prepend(label);
function selectModel(id){if(!models.some(x=>x[0]===id))id='SignHuman_Final';selector.value=id;window.avatar3dReady=false;userView=null;fitView();const version=++loadVersion;disposeModel();document.querySelector('#status').textContent='正在加载人物…';
  if(id==='sample'){loadVRM(version);return}
  const asset='/assets/3d/'+(id==='ReferenceWoman_LocalRefined'?'custom-v3/':id==='ReferenceWoman_Aligned'?'custom-v2/':id==='ReferenceWoman_Prototype'?'custom/':'valid/')+id+'.fbx';
  const loaded=root=>{if(version!==loadVersion)return;
    const lights=[];root.traverse(n=>{if(n.isLight||n.isCamera)lights.push(n);if(n.isMesh){n.frustumCulled=false;for(const m of Array.isArray(n.material)?n.material:[n.material]){m.side=THREE.DoubleSide;if(m.name==='HandSkin')m.color.setRGB(...(m.vertexColors?[1,1,1]:[.65,.43,.33]));if(m.specular)m.specular.setScalar(.08);if(m.shininess!==undefined)m.shininess=12;}}});for(const n of lights)n.removeFromParent();
    root.updateMatrixWorld(true);const box=new THREE.Box3().setFromObject(root);const height=box.max.y-box.min.y;root.scale.multiplyScalar(1.7/height);root.updateMatrixWorld(true);const fitted=new THREE.Box3().setFromObject(root);root.position.y-=fitted.min.y;root.position.x-=(fitted.max.x+fitted.min.x)/2;root.updateMatrixWorld(true);
    if(id.startsWith('SignHuman_')){userView={width:(fitted.max.x-fitted.min.x)*1.15,height:1.7,center:.85};fitView()}
    const nodes=new Map(),rest=new Map();let skinned=0;root.traverse(n=>{if(n.isSkinnedMesh)skinned++;if(n.isBone){if(!nodes.has(n.name)||n.children.length>nodes.get(n.name).children.length)nodes.set(n.name,n);rest.set(n,n.quaternion.clone())}});
    const names={leftUpperArm:'LeftArm',leftLowerArm:'LeftForeArm',leftHand:'LeftHand',rightUpperArm:'RightArm',rightLowerArm:'RightForeArm',rightHand:'RightHand'};
    for(const side of ['left','right'])for(const finger of ['Thumb','Index','Middle','Ring','Little']){const source=finger==='Little'?'Pinky':finger,segments=finger==='Thumb'?['Metacarpal','Proximal','Distal']:['Proximal','Intermediate','Distal'];for(let i=0;i<3;i++)names[side+finger+segments[i]]=side[0].toUpperCase()+side.slice(1)+'Hand'+source+(i+1)}
    vrm={scene:root,humanoid:{getNormalizedBoneNode:name=>nodes.get(names[name]),getRestRotation:name=>rest.get(nodes.get(names[name])),resetNormalizedPose:()=>{for(const [n,q] of rest)n.quaternion.copy(q);root.updateMatrixWorld(true)}},update:()=>{root.updateMatrixWorld(true)}};isFBX=true;scene.add(root);root.updateMatrixWorld(true);
    if(id.startsWith('SignHuman_'))for(const side of ['left','right'])rememberPalm(side);
    if(id==='SignHuman_Final'){const bind=new Map();for(const name of referenceNames){const n=bone(name);if(n)bind.set(name,n.getWorldQuaternion(new THREE.Quaternion()))}initializeReference(version,vrm,bind)}
    for(const [a,b] of pairs)saveDirection(a,b);
    for(const side of ['left','right']){saveDirection(side+'Hand',side+'MiddleProximal');for(const finger of ['Thumb','Index','Middle','Ring','Little']){const seg=finger==='Thumb'?['Metacarpal','Proximal','Distal']:['Proximal','Intermediate','Distal'];saveDirection(side+finger+seg[0],side+finger+seg[1]);saveDirection(side+finger+seg[1],side+finger+seg[2]);const n=bone(side+finger+seg[2]),child=n?.children.find(x=>x.isBone);if(n&&child){const d=child.getWorldPosition(new THREE.Vector3()).sub(n.getWorldPosition(new THREE.Vector3())).applyQuaternion(n.getWorldQuaternion(new THREE.Quaternion()).invert()).normalize();directions.set(side+finger+seg[2],d)}}}
    window.avatar3dReady=id!=='SignHuman_Final';document.querySelector('#status').textContent='人物已加载：'+models.find(x=>x[0]===id)[1]+'；骨骼 '+nodes.size+'，映射 '+directions.size+'，蒙皮 '+skinned+'；可发送字幕测试。';
  };
  if(id.startsWith('SignHuman_'))loader.load('/assets/3d/user/'+(id==='SignHuman_Final'?'SignHuman_CleanHands':'SignHuman_HandsOptimized')+'.glb?v=standard-hands-v1',g=>loaded(g.scene),undefined,failed);else new FBXLoader().load(asset,loaded,undefined,failed)}
selector.onchange=()=>{localStorage.setItem('avatar-model',selector.value);selectModel(selector.value)};
window.addEventListener('storage',e=>{if(e.key==='avatar-model')selectModel(e.newValue)});
if(!localStorage.getItem('user-avatar-default-v1')){localStorage.setItem('avatar-model','SignHuman_Final');localStorage.setItem('user-avatar-default-v1','1')}
selectModel(new URLSearchParams(location.search).get('model')||localStorage.getItem('avatar-model')||'SignHuman_Final');
function aim(name,a,b){const node=bone(name),rest=directions.get(name);if(!node||!rest)return;
  const direction=new THREE.Vector3(b[0]-a[0],b[1]-a[1],b[2]-a[2]);if(direction.lengthSq()<1e-10)return;
  const parentWorld=node.parent.getWorldQuaternion(new THREE.Quaternion());direction.normalize().applyQuaternion(parentWorld.invert());const bind=vrm.humanoid.getRestRotation?.(name);if(bind){node.quaternion.setFromUnitVectors(rest.clone().applyQuaternion(bind),direction).multiply(bind)}else{node.quaternion.setFromUnitVectors(rest,direction)}node.updateWorldMatrix(false,true)}
function pose(frame){vrm.humanoid.resetNormalizedPose();
  if(!frame){for(const side of ['left','right']){if(isFBX){const sign=side==='left'?1:-1;aim(side+'UpperArm',[0,0,0],[sign*.25,-1,0]);aim(side+'LowerArm',[0,0,0],[sign*.10,-1,.06]);}else{const n=bone(side+'UpperArm');if(n)n.rotation.z=side==='left'?-1.15:1.15;}}return}
  for(const [a,b,i,j] of pairs)aim(a,frame.body[i],frame.body[j]);
  for(let h=0;h<2;h++){const side=h===0?'left':'right',hand=frame.hands[h];if(isFBX&&palmBases.has(side))orientPalm(side,hand);else aim(side+'Hand',hand[0],hand[9]);
    for(let f=0;f<5;f++){const finger=['Thumb','Index','Middle','Ring','Little'][f],names=f===0?['Metacarpal','Proximal','Distal']:['Proximal','Intermediate','Distal'];
      const base=1+f*4;for(let j=0;j<3;j++)aim(side+finger+names[j],hand[base+j],hand[base+j+1]);}}
}
window.renderAvatar3D=frame=>{current=frame};
const clock=new THREE.Clock();
function render(){requestAnimationFrame(render);const w=canvas.clientWidth,h=canvas.clientHeight;const ratio=renderer.getPixelRatio();if(canvas.width!==Math.round(w*ratio)||canvas.height!==Math.round(h*ratio)){renderer.setSize(w,h,false);camera.aspect=w/h;camera.updateProjectionMatrix();fitView()}
  const dt=Math.min(clock.getDelta(),.1);if(vrm){pose(current);applyReference(current,dt);if(palmBases.size){const alpha=1-Math.exp(-dt*20);for(const name of directions.keys()){const n=bone(name);if(!n)continue;const previous=smoothRotations.get(n);if(previous){previous.slerp(n.quaternion,alpha);n.quaternion.copy(previous)}else smoothRotations.set(n,n.quaternion.clone())}}vrm.update(dt)}renderer.render(scene,camera)}render();
