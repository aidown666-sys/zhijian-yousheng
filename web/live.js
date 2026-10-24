'use strict';
const bindingReview=new URLSearchParams(location.search).get('review')==='1';
let backgroundRevision=null;
async function syncBackground(){try{
 const r=await fetch('/api/background');if(!r.ok)throw Error('背景服务不可用，请重启 start.cmd');const d=await r.json();
 if(d.revision!==backgroundRevision){backgroundRevision=d.revision;const stage=document.querySelector('.stage');stage.style.backgroundImage=d.enabled?'url("/background-image.jpg?v='+d.revision+'")':'';stage.style.backgroundSize=d.fit;stage.style.backgroundPosition='center';stage.style.backgroundRepeat='no-repeat';
 const fit=document.querySelector('#background-fit');if(fit)fit.value=d.fit;
 const label=document.querySelector('#background-status');if(label)label.textContent=d.enabled?'自定义背景已启用，采集窗口同步生效':'未使用背景图，沿用页面原背景';}
 }catch(e){backgroundRevision=null;const label=document.querySelector('#background-status');if(label)label.textContent=e.message}setTimeout(syncBackground,2000)}
syncBackground();
async function updateBackground(image){
 const label=document.querySelector('#background-status');try{
 const r=await fetch('/api/background',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({image,fit:document.querySelector('#background-fit').value})});const d=await r.json();if(!r.ok)throw Error(d.error);backgroundRevision=null;label.textContent='背景已保存，采集窗口将在两秒内更新';
 }catch(e){label.textContent=e.message}
}
document.querySelector('#background-file').onchange=async e=>{const file=e.target.files[0];if(!file)return;if(file.size>5*1024*1024){document.querySelector('#background-status').textContent='图片不能超过 5MB';return}const reader=new FileReader();reader.onload=()=>updateBackground(reader.result);reader.readAsDataURL(file)};
document.querySelector('#background-clear').onclick=()=>updateBackground(null);
document.querySelector('#background-fit').onchange=()=>updateBackground('unchanged');
if(location.pathname==='/output'){
  document.body.classList.add('output');document.title='指间有声 · 手语输出';
  const settings=new URLSearchParams(location.search),background={green:'#00ff00',blue:'#004cff',white:'#ffffff',black:'#000000'}[settings.get('bg')];
  if(background){document.body.style.background=background;document.querySelector('.stage').style.background=background}
  if(settings.get('subtitles')==='0')document.querySelector('#subtitle').hidden=true;
}
const canvas=document.querySelector('canvas'),sub=document.querySelector('#subtitle'),status=document.querySelector('#status');
let cursor=0,pending=[],active=null,start=0,last=null,samples=[],lastPlayedSeq=null;
const motionNotice=document.createElement('div');motionNotice.id='motion-notice';motionNotice.style.cssText='position:absolute;top:12px;left:12px;right:12px;padding:8px 12px;border-radius:8px;background:#101b2be8;color:#ffe2a3;font:14px system-ui;pointer-events:none';motionNotice.textContent='动作拼接研究演示，非经审核的完整手语翻译';document.querySelector('.stage').append(motionNotice);
const p=v=>[360+v[0]*650,610-v[1]*650];
function line(a,b,color,width){ctx.beginPath();ctx.moveTo(...a);ctx.lineTo(...b);ctx.strokeStyle=color;ctx.lineWidth=width;ctx.lineCap='round';ctx.stroke()}
function circle(x,y,r,color){ctx.fillStyle=color;ctx.beginPath();ctx.arc(x,y,r,0,Math.PI*2);ctx.fill()}
function draw(frame){if(window.renderAvatar3D)window.renderAvatar3D(frame)}
function tick(now){if(!active&&pending.length){active=pending.shift();lastPlayedSeq=active.seq;start=now;sub.textContent=active.text;motionNotice.textContent=active.motion.partial?'片段演示，非完整翻译｜匹配：'+active.motion.tokens.join(' / ')+'｜未表达：'+active.motion.missing.join('、'):'动作拼接研究演示，非经审核的完整手语翻译'}
  if(active){const at=(now-start)/1000*active.motion.fps,i=Math.floor(at),frames=active.motion.frames;
    if(i>=frames.length){last=frames.at(-1);active=null;start=now}else{const a=frames[i],b=frames[Math.min(i+1,frames.length-1)],t=at-i;
      const mix=(x,y)=>x.map((v,k)=>Array.isArray(v)?mix(v,y[k]):v+(y[k]-v)*t);
      last={body:mix(a.body,b.body),hands:mix(a.hands,b.hands)};}
  }else if(now-start>900)last=null;draw(last);requestAnimationFrame(tick)}requestAnimationFrame(tick);
async function poll(){try{const r=await fetch('/api/events?after='+cursor);if(!r.ok)throw Error('连接失败');const data=await r.json();if(data.latest<cursor)cursor=data.latest;
  for(const e of data.events){cursor=Math.max(cursor,e.seq);if(Date.now()/1000-e.created>15)continue;
    if(e.error){status.textContent=e.error;sub.textContent=e.text;continue}if(pending.length>=8)pending.shift();pending.push(e);status.textContent='字幕已接收，等待播放 '+pending.length+' 条。'+(e.motion.warning||'整句样本检索；手语准确性待审核。')}
  }catch(e){status.textContent='连接中断，正在重试：'+e.message}setTimeout(poll,250)}
// Start from live edge: refreshing OBS does not replay historic captions.
if(!bindingReview)fetch('/api/events').then(r=>r.json()).then(d=>{cursor=d.latest;status.textContent='已连接，等待定稿字幕';poll()}).catch(()=>poll());
if(bindingReview){
 const controls=document.createElement('div');controls.style.cssText='position:fixed;bottom:10px;left:10px;right:10px;z-index:10;background:#101b2be8;padding:8px;color:white';controls.textContent='离线绑定检查（不接收或发送直播字幕）：';document.body.append(controls);
 fetch('/assets/3d/user/review-motion.json').then(r=>r.json()).then(motion=>{for(const frame of [0,10,20,30,40,50]){const button=document.createElement('button');button.textContent='第 '+frame+' 帧';button.onclick=()=>{active=null;pending=[];last=motion.frames[frame];start=performance.now()+1e12;sub.textContent='离线检查：'+motion.text+' · 第 '+frame+' 帧';motionNotice.textContent='离线绑定检查 · 固定动作帧 · 非直播字幕';};controls.append(button);if(frame===20)button.click()}}).catch(e=>controls.textContent='离线动作读取失败：'+e.message);
}
async function send(text){const r=await fetch('/api/captions',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:crypto.randomUUID(),text,final:true})});const d=await r.json();status.textContent=d.error||('字幕状态：'+d.status)}
document.querySelector('#send').onclick=()=>send(document.querySelector('#text').value);
document.querySelector('#clear').onclick=()=>{pending=[];active=null;last=null;sub.textContent='已清空';status.textContent='当前页面播放队列已清空'};
function options(){const q=document.querySelector('#search').value;const select=document.querySelector('#samples');select.replaceChildren();for(const text of samples.filter(x=>x.includes(q)).slice(0,150)){const o=document.createElement('option');o.textContent=text;select.append(o)}}
document.querySelector('#search').oninput=options;document.querySelector('#samples').onchange=e=>document.querySelector('#text').value=e.target.value;
fetch('/api/samples').then(r=>r.json()).then(d=>{samples=d.samples;options()}).catch(e=>status.textContent=e.message);
document.querySelector('#demo').onclick=async()=>{for(const text of ['他今年四岁。',...samples.filter(x=>x.length<15).slice(0,2)])await send(text)};
const modeSelect=document.createElement('select');modeSelect.id='motion-mode';modeSelect.setAttribute('aria-label','缺词处理模式');modeSelect.innerHTML='<option value="preview">流程演示：播放已匹配片段，明确标出缺词</option><option value="strict">严格模式：有缺词就整句停止</option>';
const modeLabel=document.createElement('label');modeLabel.textContent='缺词处理（片段演示不能作为完整手语翻译）';modeLabel.append(modeSelect);document.querySelector('section').prepend(modeLabel);
fetch('/api/motion-settings').then(r=>r.json()).then(d=>{modeSelect.value=d.mode;modeLabel.prepend(document.createTextNode('词动作 '+d.words+' 个；整句 '+d.sentences+' 条。'))}).catch(()=>{});
modeSelect.onchange=async()=>{try{const r=await fetch('/api/motion-settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({mode:modeSelect.value})});if(!r.ok)throw Error('保存失败');status.textContent='模式已保存，对后续字幕生效；片段演示只播放已匹配动作，不表示完整句意。'}catch(e){status.textContent=e.message}};
if(location.pathname==='/output'&&!bindingReview){
 const clientId=crypto.randomUUID();
 async function outputHeartbeat(){try{await fetch('/api/output-heartbeat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({client_id:clientId,ready:window.avatar3dReady===true,playing:!!active,last_seq:lastPlayedSeq})})}catch{}setTimeout(outputHeartbeat,2000)}outputHeartbeat();
}

if(location.pathname!=='/output'){
 async function bridgeState(){try{const r=await fetch('/api/bridge-status');if(!r.ok)throw Error();const d=await r.json();
 if(d.updated&&Date.now()/1000-d.updated>12){d.state='stale';d.error='字幕桥接心跳超时；请查看诊断页，服务会自动重启已退出的桥接进程'};
 const names={stale:'心跳超时',not_started:'尚未启动',connected:'已连接，等待新增字幕',receiving:'正在接收字幕',error:'连接异常'};
 document.querySelector('#bridge-status').textContent='保利威字幕桥接：'+(d.source==='watch-socket'?'观看页 WebSocket；':'')+(names[d.state]||d.state)+(d.error?'；'+d.error:'')+(d.source==='watch-socket'?'；已接收 '+(d.received_count||0)+' 句；动作入队 '+(d.forwarded_count||0)+' 句（其中片段 '+(d.partial_count||0)+' 句）；失败 '+(d.unsupported_count||0)+' 句':d.relay?.last_increment?'；已观察到字幕增量':'；尚未确认直播中的逐句字幕');
 }catch{document.querySelector('#bridge-status').textContent='保利威桥接状态暂不可读，请检查本地服务'}setTimeout(bridgeState,2000)}bridgeState();
}
