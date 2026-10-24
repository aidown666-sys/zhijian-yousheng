"""Local 3D subtitle-to-motion prototype: sentence or experimental word retrieval."""
import io
import json
import pickle
import threading
import time
import sys
import subprocess
import re
import base64
from functools import lru_cache
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

sys.path.insert(0,str(Path(__file__).resolve().parent/'runtime/pose_packages'))
import lmdb
import numpy as np
from tools.pose_control import joints

ROOT = Path(__file__).resolve().parent
BACKGROUND_LOCK=threading.Lock()


def background_settings():
    try:return json.loads((ROOT/'runtime/background.json').read_text(encoding='utf8'))
    except (OSError,ValueError):return {'enabled':False,'fit':'cover','revision':0}


def save_background(payload):
    from PIL import Image,ImageOps
    fit=payload.get('fit','cover')
    if fit not in ('cover','contain'):raise ValueError('背景显示方式无效')
    with BACKGROUND_LOCK:
        settings=background_settings();image=payload.get('image','unchanged')
        if image is None:settings['enabled']=False
        elif image!='unchanged':
            if not isinstance(image,str) or not image.startswith(('data:image/png;base64,','data:image/jpeg;base64,','data:image/webp;base64,')):raise ValueError('请选择 PNG/JPEG/WebP 图片')
            raw=base64.b64decode(image.split(',',1)[1],validate=True)
            if len(raw)>5*1024*1024:raise ValueError('背景图不能超过 5MB')
            try:
                with Image.open(io.BytesIO(raw)) as im:
                    if im.width*im.height>25000000:raise ValueError('图片分辨率过大')
                    im=ImageOps.exif_transpose(im).convert('RGB');im.thumbnail((4096,4096))
                    im.save(ROOT/'runtime/background.jpg','JPEG',quality=92)
            except (OSError,Image.DecompressionBombError):raise ValueError('无法读取背景图片')
            settings['enabled']=True
        settings.update(fit=fit,revision=time.time_ns())
        temp=ROOT/'runtime/background.tmp';temp.write_text(json.dumps(settings),encoding='utf8');temp.replace(ROOT/'runtime/background.json')
        return settings


def normalize(text):
    return re.sub(r'[\s。，！？,.!?]', '', text)


def motion_settings():
    try:return json.loads((ROOT/'runtime/motion-settings.json').read_text(encoding='utf8'))
    except (OSError,ValueError):return {'mode':'preview'}


class MotionLibrary:
    def __init__(self):
        self.env = lmdb.open(str(ROOT/'data/lmdb/dev/CSL-Daily_reopt_dev.lmdb'), readonly=True, lock=False)
        self.index = {}
        with self.env.begin() as txn:
            ids=pickle.loads(txn.get(b'__meta__'))['clip_ids']
            for clip in ids:
                with np.load(io.BytesIO(txn.get(clip.encode())), allow_pickle=True) as data:
                    text = str(data['translation'][0])
                    self.index.setdefault(normalize(text), (clip, text))
        self.words = {}
        rows=pickle.loads((ROOT/'data/sign_dictionary/csl_iso.dev').read_bytes())
        for row in rows:
            if row['video_file'] in ids and row['end']>row['start']:
                self.words.setdefault(row['label'],row)
        self.by_first={}
        for word in self.words:self.by_first.setdefault(word[0],[]).append(word)
        for words in self.by_first.values():words.sort(key=len,reverse=True)

    @lru_cache(maxsize=512)
    def word_frames(self,word):
        row=self.words[word]
        with self.env.begin() as txn:raw=txn.get(row['video_file'].encode())
        frames=[]
        with np.load(io.BytesIO(raw),allow_pickle=True) as data:
            for i in range(row['start'],min(row['end'],len(data['segment']))):
                body,hands=joints(data['body_features'][i],data['left_features'][i],data['right_features'][i])
                frames.append({'body':body.round(5).tolist(),'hands':[h.round(5).tolist() for h in hands]})
        return frames

    def compose(self,text,allow_partial=False):
        clean=re.sub(r'[\s，。！？、；：,.!?;:“”‘’（）()\"\-]','',text)
        # Dynamic programming minimizes unsupported characters, then word count.
        n=len(clean);best=[None]*(n+1);best[n]=(0,0,[],[])
        for i in range(n-1,-1,-1):
            tail=best[i+1];options=[(tail[0]+1,tail[1]+1,tail[2],[clean[i]]+tail[3])]
            for word in self.by_first.get(clean[i],[]):
                if clean.startswith(word,i):
                    t=best[i+len(word)];options.append((t[0],t[1]+1,[word]+t[2],t[3]))
            best[i]=min(options,key=lambda x:(x[0],x[1]))
        if not clean:raise ValueError('字幕没有可识别内容。')
        _,_,tokens,missing=best[0]
        if missing and not allow_partial:raise ValueError('缺少这些字/词的动作：'+ '、'.join(dict.fromkeys(missing))+'。未播放不完整的替代动作。')
        if not tokens:raise ValueError('本句没有匹配到可播放的词动作。')
        if len(tokens)>40:raise ValueError('字幕过长，请分成最多 40 个词的短句。')
        frames=[]
        def blend(a,b,t):
            if isinstance(a,list):return [blend(x,y,t) for x,y in zip(a,b)]
            return a+(b-a)*t
        for word in tokens:
            clip=self.word_frames(word)
            if not clip:raise ValueError('词动作为空：'+word)
            if frames:
                previous=frames[-1]
                for j in range(1,6):frames.append({k:blend(previous[k],clip[0][k],j/6) for k in ('body','hands')})
            frames.extend(clip)
        return {'text':text,'fps':25,'frames':frames,'tokens':tokens,'experimental':True,
                'missing':list(dict.fromkeys(missing)),'partial':bool(missing),'coverage':round((len(clean)-len(missing))/len(clean),3),
                'method':'partial-word-preview' if missing else 'word-concatenation',
                'warning':'片段演示，非完整手语翻译；未表达：'+'、'.join(dict.fromkeys(missing)) if missing else '逐词动作拼接实验；沿用中文词序，未完成手语语法转换，过渡及语义未经审核。'}

    def motion(self, text,allow_partial=False):
        match = self.index.get(normalize(text))
        if not match:
            return self.compose(text,allow_partial=allow_partial)
        clip, matched = match
        with self.env.begin() as txn:
            raw = txn.get(clip.encode())
        frames = []
        with np.load(io.BytesIO(raw), allow_pickle=True) as data:
            for b, l, r in zip(data['body_features'], data['left_features'], data['right_features']):
                body, hands = joints(b, l, r)
                frames.append({'body': body.round(5).tolist(), 'hands': [h.round(5).tolist() for h in hands]})
        return {'clip': clip, 'text': matched, 'fps': 25, 'frames': frames,
                'experimental': True, 'method': 'exact-sentence retrieval; approximate skeleton'}


class Stream:
    def __init__(self, library,live_settings=False):
        self.library = library
        self.live_settings=live_settings
        self.events = deque(maxlen=100)
        self.seen = deque(maxlen=1000)
        self.lock = threading.Lock()
        self.sequence = 0
        self.outputs = {}

    def submit(self, payload):
        text = payload.get('text')
        if not isinstance(text, str) or not 0 < len(text.strip()) <= 500:
            raise ValueError('text 必须是 1～500 字的字幕。')
        if not isinstance(payload.get('final', True), bool):
            raise ValueError('final 必须是布尔值。')
        if not payload.get('final', True):
            return {'status': 'partial_ignored'}
        event_id = payload.get('id')
        if event_id is not None and (not isinstance(event_id, str) or len(event_id) > 200):
            raise ValueError('id 必须是最多 200 字符的字符串。')
        with self.lock:
            if event_id and event_id in self.seen:
                return {'status': 'duplicate'}
            try:
                motion = self.library.motion(text,allow_partial=self.live_settings and motion_settings()['mode']=='preview')
                error = None
            except ValueError as exc:
                motion, error = None, str(exc)
            self.sequence += 1
            event = {'seq': self.sequence, 'text': text.strip(), 'created': time.time(),
                     'motion': motion, 'error': error}
            self.events.append(event)
            if event_id:
                self.seen.append(event_id)
            return {'status': 'queued' if motion else 'unsupported', 'seq': self.sequence, 'error': error,
                    'partial':bool(motion and motion.get('partial')),'warning':motion.get('warning') if motion else None}


def make_handler(stream):
    class Handler(BaseHTTPRequestHandler):
        def reply(self, status, data):
            raw = json.dumps(data, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            url = urlparse(self.path)
            if url.path=='/api/background':return self.reply(200,background_settings())
            if url.path=='/api/motion-settings':return self.reply(200,{**motion_settings(),'words':len(stream.library.words),'sentences':len(stream.library.index)})
            if url.path=='/background-image.jpg':
                with BACKGROUND_LOCK:
                    file=ROOT/'runtime/background.jpg'
                    if not file.is_file():return self.reply(404,{'error':'尚未上传背景图'})
                    raw=file.read_bytes()
                self.send_response(200);self.send_header('Content-Type','image/jpeg');self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(raw);return
            if url.path == '/api/samples':
                return self.reply(200, {'samples': [x[1] for x in stream.library.index.values()], 'word_count':len(stream.library.words),'scope': 'sentence retrieval or experimental word concatenation'})
            if url.path == '/api/bridge-status':
                file=ROOT/'runtime/polyv-bridge-status.json'
                try:
                    data=json.loads(file.read_text(encoding='utf8')) if file.is_file() else {'state':'not_started'}
                except (ValueError,OSError):data={'state':'unknown'}
                return self.reply(200,data)
            if url.path == '/api/diagnostics':
                try:bridge=json.loads((ROOT/'runtime/polyv-bridge-status.json').read_text(encoding='utf8'))
                except (OSError,ValueError):bridge={'state':'not_started'}
                with stream.lock:
                    events=[{'seq':e['seq'],'text':e['text'],'created':e['created'],'error':e['error'],
                        'method':e['motion']['method'] if e['motion'] else None,'warning':e['motion'].get('warning') if e['motion'] else None,'frames':len(e['motion']['frames']) if e['motion'] else 0} for e in list(stream.events)[-10:]]
                    outputs=[x for x in stream.outputs.values() if time.time()-x['last_seen']<12]
                return self.reply(200,{'now':time.time(),'bridge':bridge,'events':events,'outputs':outputs})
            if url.path == '/diagnostics':
                raw=(ROOT/'web/diagnostics.html').read_bytes();self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw);return
            if url.path == '/api/events':
                try:
                    after = int(parse_qs(url.query).get('after', ['0'])[0])
                except ValueError:
                    return self.reply(400, {'error': 'after 必须为整数。'})
                with stream.lock:
                    return self.reply(200, {'events': [x for x in stream.events if x['seq'] > after], 'latest': stream.sequence})
            if url.path.startswith(('/vendor/', '/assets/3d/')) or url.path == '/avatar3d.js':
                base = ROOT/'web' if not url.path.startswith('/assets/') else ROOT
                file = (base/url.path.lstrip('/')).resolve()
                allowed=(ROOT/'assets/3d') if url.path.startswith('/assets/3d/') else (ROOT/'web/vendor') if url.path.startswith('/vendor/') else ROOT/'web'
                if not file.is_relative_to(allowed.resolve()) or not file.is_file() or file.suffix not in ('.js', '.vrm', '.json', '.fbx', '.glb'):
                    return self.reply(404, {'error': 'not found'})
                raw = file.read_bytes()
                self.send_response(200)
                self.send_header('Content-Type', 'text/javascript' if file.suffix == '.js' else 'application/octet-stream')
                self.send_header('Content-Length', str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
                return
            if url.path not in ('/', '/output', '/live.js'):
                return self.reply(404, {'error': 'not found'})
            file = ROOT/'web'/('live.js' if url.path == '/live.js' else 'live.html')
            raw = file.read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', 'text/javascript; charset=utf-8' if file.suffix == '.js' else 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_POST(self):
            if self.headers.get('Origin') not in (None, 'http://127.0.0.1:8877', 'http://localhost:8877'):
                return self.reply(403, {'error': '不允许跨站提交。'})
            if urlparse(self.path).path not in ('/api/captions','/api/output-heartbeat','/api/background','/api/motion-settings'):
                return self.reply(404, {'error': 'not found'})
            try:
                size = int(self.headers.get('Content-Length', 0))
                limit=7*1024*1024 if urlparse(self.path).path=='/api/background' else 8192
                if not 0 < size <= limit:
                    raise ValueError('请求长度错误。')
                payload = json.loads(self.rfile.read(size))
                if not isinstance(payload, dict):
                    raise ValueError('请求必须为 JSON 对象。')
                if urlparse(self.path).path=='/api/motion-settings':
                    mode=payload.get('mode')
                    if mode not in ('strict','preview'):raise ValueError('动作模式无效')
                    data={'mode':mode}
                    with BACKGROUND_LOCK:
                        temp=ROOT/'runtime/motion-settings.tmp';temp.write_text(json.dumps(data),encoding='utf8');temp.replace(ROOT/'runtime/motion-settings.json')
                    return self.reply(200,data)
                if urlparse(self.path).path=='/api/background':return self.reply(200,save_background(payload))
                if urlparse(self.path).path == '/api/output-heartbeat':
                    client=payload.get('client_id')
                    if not isinstance(client,str) or not 1<=len(client)<=100:raise ValueError('Invalid output client id')
                    with stream.lock:
                        stream.outputs[client]={'client_id':client,'last_seen':time.time(),'ready':payload.get('ready') is True,
                            'playing':payload.get('playing') is True,'last_seq':payload.get('last_seq') if isinstance(payload.get('last_seq'),int) else None}
                        stream.outputs={k:v for k,v in stream.outputs.items() if time.time()-v['last_seen']<30}
                    return self.reply(200,{'ok':True})
                return self.reply(202, stream.submit(payload))
            except (ValueError, TypeError) as exc:
                return self.reply(400, {'error': str(exc)})
    return Handler


if __name__ == '__main__':
    library = MotionLibrary()
    print(f'{len(library.index)} sentences loaded. http://127.0.0.1:8877', flush=True)
    bridge=None;bridge_log=None;bridge_stop=threading.Event();bridge_guard=None
    watch_config=ROOT/'integrations/polyv/watch-config.json'
    if watch_config.is_file() or (ROOT/'integrations/polyv/local-bridge.json').is_file():
        bridge_log=(ROOT/'runtime/polyv-bridge.log').open('a',encoding='utf8')
        command=[sys.executable,str(ROOT/'integrations/polyv/watch_bridge.py'),'--url',json.loads(watch_config.read_text(encoding='utf8'))['watch_url']] if watch_config.is_file() else [sys.executable,str(ROOT/'integrations/polyv/bridge.py')]
        bridge=subprocess.Popen(command,cwd=ROOT,
            stdout=bridge_log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        def supervise_bridge():
            global bridge
            while not bridge_stop.wait(3):
                if bridge.poll() is not None:
                    bridge=subprocess.Popen(command,cwd=ROOT,stdout=bridge_log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        bridge_guard=threading.Thread(target=supervise_bridge,daemon=True);bridge_guard.start()
    try:
        ThreadingHTTPServer(('127.0.0.1', 8877), make_handler(Stream(library,live_settings=True))).serve_forever()
    finally:
        bridge_stop.set()
        if bridge_guard:bridge_guard.join(timeout=5)
        if bridge and bridge.poll() is None:
            bridge.terminate();bridge.wait(timeout=5)
        if bridge_log:bridge_log.close()
