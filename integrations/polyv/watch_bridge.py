"""Public-viewer subtitle bridge. Uses normal guest auth, never derives tokens."""
import json, time, threading, urllib.request, urllib.parse, argparse, http.cookiejar,sys
from collections import deque
from pathlib import Path
from bridge import ROOT, write_status, deliver
sys.path.insert(0,str(ROOT/'runtime/pose_packages'))
import websocket


HTTP=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

def request(url, data=None, headers=None, timeout=35):
    req=urllib.request.Request(url,data=data,headers={'User-Agent':'Mozilla/5.0','Accept':'application/json',**(headers or {})})
    with HTTP.open(req,timeout=timeout) as r:
        raw=r.read(4*1024*1024+1)
        if len(raw)>4*1024*1024:raise ValueError('Response too large')
        return raw.decode('utf-8'),r.headers


def packets(raw):
    """Engine.IO 3 text payload lengths count JavaScript UTF-16 units."""
    out=[]
    while raw:
        length,sep,rest=raw.partition(':')
        if not sep or not length.isdigit():raise ValueError('Invalid Engine.IO payload')
        needed=int(length);units=0;end=0
        while end<len(rest) and units<needed:
            units+=2 if ord(rest[end])>0xffff else 1;end+=1
        if units!=needed:raise ValueError('Truncated Engine.IO payload')
        out.append(rest[:end]);raw=rest[end:]
    return out


class Captions:
    def __init__(self):self.text='';self.index=None;self.valid=False;self.seen=deque(maxlen=1000)
    def accept(self,message):
        if message.get('EVENT')!='ADD' or message.get('language')!='Chinese':return None
        index=message.get('index')
        if index is None:return None
        if self.index!=index:self.text='';self.index=index;self.valid=False
        text=message.get('text')
        if not isinstance(text,str):return None
        replace=message.get('replaceIndex')
        if message.get('sliceType')==0 or replace==0 or replace is None:self.valid=True
        if not self.valid:return None
        old=self.text.encode('utf-16-le')
        if isinstance(replace,int) and 0<=replace<=len(old)//2:
            self.text=old[:replace*2].decode('utf-16-le',errors='replace')+text
        else:self.text=text
        if message.get('sliceType')!=2:return None
        final=self.text.strip();self.text=''
        if not final or index in self.seen:return None
        self.seen.append(index)
        return {'id':str(index),'text':final}


class Viewer:
    def __init__(self,url):
        p=urllib.parse.urlsplit(url)
        import re
        match=re.fullmatch(r'/watch/(\d+)/?',p.path)
        if p.scheme!='https' or not p.hostname or not p.hostname.endswith('.live.plvideo.net') or not match or p.port not in (None,443):
            raise ValueError('请填写 https://账号.live.plvideo.net/watch/频道号')
        self.base='https://'+p.hostname;self.channel=match[1]
    def api(self,path,params=None,post=False):
        query={'channelId':self.channel,**(params or {})}
        raw,headers=request(self.base+path+'?'+urllib.parse.urlencode(query),b'{}' if post else None,{'Content-Type':'application/json'})
        value=json.loads(raw)
        if value.get('code')!=200:raise ValueError('观看接口拒绝请求，请确认观看权限')
        return value['data'],headers
    def authorize(self):
        detail,_=self.api('/v3/common/channel/detail')
        settings=detail.get('authSetting',{}).get('authSettings',[])
        if not any(x.get('authType')=='none' for x in settings):
            raise ValueError('该频道需要登录/密码/付费等观看授权，暂不支持自动游客接入')
        user,headers=self.api('/v3/common/auth/none-auth/viewer/set-info',post=True)
        token=headers.get('x-auth-token')
        if not token:raise ValueError('未取得游客观看会话')
        info,_=self.api('/v3/common/channel/viewer',{'xSessdata':token})
        chat=(info.get('chatInfo') or {}).get('chatToken')
        if not chat:raise ValueError('观看接口未返回聊天凭据')
        live=info.get('liveStatus') or detail.get('liveStatus') or {}
        session=live.get('channelSessionId','')
        domain=(detail.get('domain') or {}).get('chatWsDomain','chat.polyv.net')
        host=urllib.parse.urlsplit(domain if '://' in domain else 'https://'+domain).hostname
        if not host or not (host=='chat.polyv.net' or host.endswith('.polyv.net')):raise ValueError('不支持的聊天服务域名')
        self.socket='wss://'+host+'/socket.io/?'+urllib.parse.urlencode({'EIO':3,'transport':'websocket','version':'3.0','token':chat})
        self.ws=websocket.create_connection(self.socket,timeout=35,origin=self.base,enable_multithread=True)
        packet=self.ws.recv()
        if not packet.startswith('0'):raise ValueError('Invalid Engine.IO handshake')
        hello=json.loads(packet[1:]);self.interval=hello['pingInterval']/1000
        self.session=session;self.closed=threading.Event();self.post_lock=threading.Lock()
        self.last_pong=time.monotonic();self.connected_at=time.monotonic()
        if self.ws.recv()!='40':raise ValueError('Socket.IO namespace not ready')
        login={'EVENT':'LOGIN','values':[user.get('nickname') or '字幕手语接收',user.get('avatar') or '',user['viewerId']],
               'channelId':self.channel,'roomId':self.channel,'type':'student'}
        if session:login['sessionId']=session
        self.send('420'+json.dumps(['message',json.dumps(login,ensure_ascii=True,separators=(',',':'))],ensure_ascii=True,separators=(',',':')))
        self.ws.settimeout(3)
        threading.Thread(target=self.ping,daemon=True).start()
    def send(self,packet):
        with self.post_lock:self.ws.send(packet)
    def ping(self):
        while not self.closed.wait(min(20,self.interval*.7)):
            try:self.send('2')
            except Exception:self.closed.set();return
    def messages(self):
        while not self.closed.is_set():
            if time.monotonic()-self.last_pong>max(45,self.interval*2+10):raise ConnectionError('Heartbeat expired')
            if time.monotonic()-self.connected_at>600:raise ConnectionError('Refresh viewer session')
            try:packet=self.ws.recv()
            except websocket.WebSocketTimeoutException:
                write_status(last_poll=time.time());yield None;continue
            for packet in [packet]:
                if packet=='3':self.last_pong=time.monotonic()
                if packet.startswith('430'):
                    ack=json.loads(packet[3:]);code=str(ack[0]) if ack else ''
                    if not code.startswith('2'):raise ValueError('聊天登录被拒绝')
                    write_status(state='connected',login_confirmed=True,error=None,note='聊天登录成功，等待实时字幕')
                if packet.startswith('42'):
                    pos=packet.find('[')
                    event=json.loads(packet[pos:])
                    if event[0]=='subtitles' and len(event)>1:
                        value=json.loads(event[1]) if isinstance(event[1],str) else event[1]
                        if isinstance(value,dict):yield value
                if not packet or packet=='1' or packet.startswith('41'):raise ValueError('聊天连接关闭')
                write_status(last_poll=time.time())


def main():
    p=argparse.ArgumentParser();p.add_argument('--url',default='https://10688df483.live.plvideo.net/watch/8662629');p.add_argument('--observe-seconds',type=int,default=0)
    args=p.parse_args()
    import msvcrt
    guard=open(ROOT/'runtime/polyv-bridge.lock','a+b');guard.seek(0);guard.write(b'1');guard.flush();guard.seek(0)
    try:msvcrt.locking(guard.fileno(),msvcrt.LK_NBLCK,1)
    except OSError:print('Another subtitle bridge is running',flush=True);return
    received=forwarded=unsupported=partial=0;begin=time.time();seen=deque(maxlen=1000)
    write_status(source='watch-socket',state='starting',started=begin,received_count=0,forwarded_count=0,unsupported_count=0,partial_count=0,relay={},login_confirmed=False,error=None)
    while True:
        viewer=Viewer(args.url)
        try:
            viewer.authorize();captions=Captions()
            write_status(state='connecting',channel_id=viewer.channel,session=viewer.session,error=None,login_confirmed=False)
            for msg in viewer.messages():
                if args.observe_seconds and time.time()-begin>=args.observe_seconds:return
                if msg is None:continue
                write_status(last_socket_caption=time.time(),last_partial=msg.get('text','')[:500])
                event=captions.accept(msg)
                if event:
                    key=viewer.session+':'+event['id']
                    if key in seen:continue
                    seen.append(key);event['id']='watch:'+viewer.channel+':'+key
                    received+=1
                    result={'status':'observed'} if args.observe_seconds else deliver({'local_url':'http://127.0.0.1:8877/api/captions'},event)
                    forwarded+=result['status']=='queued';unsupported+=result['status']=='unsupported'
                    partial+=bool(result.get('partial'))
                    write_status(state='receiving',received_count=received,forwarded_count=forwarded,unsupported_count=unsupported,partial_count=partial,last_caption=event['text'],last_delivered=time.time(),result=result['status'],conversion_error=result.get('error'),motion_warning=result.get('warning'),error=None)
                    print(json.dumps({'text':event['text'],'result':result['status']},ensure_ascii=True),flush=True)
                if args.observe_seconds and time.time()-begin>=args.observe_seconds:return
        except Exception as exc:
            # Never include URLs/HTTP exception strings: query contains live credentials.
            write_status(state='error',error='观看字幕连接失败（'+type(exc).__name__+'）；请检查网络、频道状态及观看权限',login_confirmed=False)
            print('Watch bridge reconnecting: '+type(exc).__name__,flush=True)
            if args.observe_seconds and time.time()-begin>=args.observe_seconds:return
            time.sleep(3)
        finally:
            if hasattr(viewer,'closed'):viewer.closed.set()
            if hasattr(viewer,'ws'):viewer.ws.close()


if __name__=='__main__':main()
