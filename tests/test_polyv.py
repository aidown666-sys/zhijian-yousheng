import importlib.util,json,os,subprocess,tempfile,time,unittest,urllib.request,urllib.error,hashlib,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


class LocalAssetIsolationTest(unittest.TestCase):
    def test_assets_cannot_escape_to_relay_configuration(self):
        import threading
        from http.server import ThreadingHTTPServer
        from live_server import make_handler
        server=ThreadingHTTPServer(('127.0.0.1',0),make_handler(None))
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            url='http://127.0.0.1:'+str(server.server_port)+'/assets/3d/../../integrations/polyv/local-bridge.json'
            with self.assertRaises(urllib.error.HTTPError) as result:urllib.request.urlopen(url,timeout=2)
            self.assertEqual(result.exception.code,404)
        finally:server.shutdown();server.server_close();thread.join()


class PolyvHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        php=ROOT/'runtime/php-test83/php.exe'
        if not php.is_file():
            installed=shutil.which('php')
            if not installed:raise unittest.SkipTest('Optional PHP test runtime unavailable')
            php=Path(installed)
        cls.temp=tempfile.TemporaryDirectory();cls.token='test-consumer-'+'x'*40;cls.producer='test-producer-'+'y'*40
        cfg={'channel_id':'8662629','app_secret':'unit-test-secret','callback_hash':'md5','consumer_token':cls.token,'producer_token':cls.producer,'state_dir':cls.temp.name}
        file=Path(cls.temp.name)/'config.php';file.write_text('<?php return json_decode('+repr(json.dumps(cfg))+',true);',encoding='utf8')
        env={**os.environ,'POLYV_SIGN_CONFIG':str(file)}
        cls.process=subprocess.Popen([str(php),'-n','-S','127.0.0.1:18891','-t',str(ROOT/'integrations/polyv/server')],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        for _ in range(50):
            try:urllib.request.urlopen('http://127.0.0.1:18891/index.php',timeout=.2);break
            except OSError:time.sleep(.05)

    @classmethod
    def tearDownClass(cls):
        cls.process.terminate();cls.process.wait(timeout=5);cls.temp.cleanup()

    def request(self,path,payload=None,token=None):
        headers={'Content-Type':'application/json'}
        if token:headers['Authorization']='Bearer '+token
        req=urllib.request.Request('http://127.0.0.1:18891/'+path,data=json.dumps(payload).encode() if payload is not None else None,headers=headers)
        with urllib.request.urlopen(req,timeout=5) as response:return json.load(response)

    def test_unauthenticated_poll_is_rejected(self):
        with self.assertRaises(urllib.error.HTTPError) as caught:self.request('poll.php')
        self.assertEqual(caught.exception.code,401)

    def test_ingest_poll_and_duplicate(self):
        payload={'id':'http-test-1','channelId':'8662629','text':'今天我去学校','final':True}
        a=self.request('ingest.php',payload,self.producer);b=self.request('ingest.php',payload,self.producer)
        self.assertEqual(a['latest'],b['latest'])
        result=self.request('poll.php',token=self.token)
        self.assertEqual(result['events'][-1]['text'],payload['text'])

    def test_callback_bad_signature_rejected(self):
        with self.assertRaises(urllib.error.HTTPError) as caught:self.request('callback.php',{'channelId':8662629})
        self.assertEqual(caught.exception.code,403)

    def test_callback_filters_translated_subtitles(self):
        ts=str(int(time.time()*1000));sign=hashlib.md5(('unit-test-secret'+ts).encode()).hexdigest()
        result=self.request('callback.php?timestamp='+ts+'&sign='+sign,{'channelId':8662629,'source':'chatRealtimeSrt','language':'English','isOriginal':'N'})
        self.assertIn('ignored',result['status'])
        diagnostic=self.request('poll.php',token=self.token)['status']
        self.assertEqual(diagnostic['diagnostic_version'],2)
        self.assertEqual(diagnostic['last_callback_http'],200)
        self.assertIn('filtered',diagnostic['last_callback_result'])
        self.assertGreaterEqual(diagnostic['callback_attempts'],1)

    def test_wrong_channel_rejected(self):
        with self.assertRaises(urllib.error.HTTPError) as caught:self.request('ingest.php',{'id':'bad','text':'test','channelId':'1','final':True},self.producer)
        self.assertEqual(caught.exception.code,403)


if __name__=='__main__':unittest.main()
