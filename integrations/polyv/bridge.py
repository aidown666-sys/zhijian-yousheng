"""Authenticated outbound relay polling. No appSecret leaves the PHP server."""
import json,time,urllib.request,urllib.parse,urllib.error,sys,threading,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
STATUS=ROOT/'runtime/polyv-bridge-status.json'
CURRENT={}
STATUS_LOCK=threading.Lock()


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        return None


def write_status(**value):
    # Windows readers/antivirus may briefly deny replace. Telemetry must never
    # bring down the actual caption receiver, including its error handler.
    with STATUS_LOCK:
        CURRENT.update(value)
        temp=STATUS.with_suffix('.'+str(os.getpid())+'.tmp')
        try:
            STATUS.parent.mkdir(exist_ok=True)
            temp.write_text(json.dumps({'updated':time.time(),**CURRENT},ensure_ascii=False),encoding='utf8')
            for attempt in range(4):
                try:temp.replace(STATUS);return True
                except PermissionError:
                    if attempt<3:time.sleep(.025*(attempt+1))
            return False
        except OSError:return False


def get_events(config,cursor):
    url=config['relay_url']+'?'+urllib.parse.urlencode({'after':cursor})
    if urllib.parse.urlsplit(url).scheme!='https':raise ValueError('Relay must use HTTPS')
    req=urllib.request.Request(url,headers={'Authorization':'Bearer '+config['consumer_token'],'Accept':'application/json'})
    with urllib.request.build_opener(NoRedirect).open(req,timeout=12) as response:
        raw=response.read(4194305)
        if len(raw)>4194304:raise ValueError('Relay response too large')
        return json.loads(raw)


def deliver(config,event):
    local=urllib.parse.urlsplit(config['local_url'])
    if local.hostname not in ('127.0.0.1','localhost') or local.scheme!='http':raise ValueError('Local destination must be loopback HTTP')
    payload={'id':'polyv:'+str(event['id']),'text':event['text'],'final':True}
    req=urllib.request.Request(config['local_url'],data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=10) as response:return json.load(response)


def main():
    path=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).with_name('local-bridge.json')
    config=json.loads(path.read_text(encoding='utf8'));cursor=None
    import msvcrt
    guard=open(ROOT/'runtime/polyv-bridge.lock','a+b');guard.seek(0);guard.write(b'1');guard.flush();guard.seek(0)
    try:msvcrt.locking(guard.fileno(),msvcrt.LK_NBLCK,1)
    except OSError:
        print('Subtitle bridge is already running. Open http://127.0.0.1:8877/diagnostics');return
    write_status(state='starting',started=time.time(),received_count=0,forwarded_count=0,unsupported_count=0,error=None)
    print('Subtitle bridge started. Diagnostics: http://127.0.0.1:8877/diagnostics',flush=True)
    received=forwarded=unsupported=0
    while True:
        try:
            data=get_events(config,0 if cursor is None else cursor)
            if cursor is None or data['latest']<cursor:
                cursor=data['latest'];write_status(state='connected',error=None,note='从当前字幕位置开始，历史字幕不回放',relay=data.get('status',{}))
            else:
                for event in data['events']:
                    if time.time()-event['created']>config.get('max_age_seconds',15):cursor=max(cursor,event['seq']);continue
                    received+=1
                    result=deliver(config,event)
                    if result['status']=='queued':forwarded+=1
                    if result['status']=='unsupported':unsupported+=1
                    cursor=max(cursor,event['seq'])
                    write_status(state='receiving',result=result['status'],conversion_error=result.get('error'),error=None,last_caption=event['text'],last_delivered=time.time(),received_count=received,forwarded_count=forwarded,unsupported_count=unsupported,relay=data.get('status',{}))
                if not data['events']:write_status(state='connected',error=None,note='等待新增字幕',relay=data.get('status',{}))
        except urllib.error.HTTPError as error:
            write_status(state='error',error='HTTP '+str(error.code)+'；检查部署、consumer token 和本地服务')
        except (OSError,ValueError,KeyError,TypeError):
            write_status(state='error',error='连接失败或返回格式不符；请检查服务器部署和网络')
        time.sleep(max(1,config.get('poll_seconds',1)))


if __name__=='__main__':main()
