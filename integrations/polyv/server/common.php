<?php
declare(strict_types=1);
// PHP 7.4+, cURL. No SDK credentials are returned to clients.
function config(): array {
    static $config;
    if ($config === null) {
        $file = getenv('POLYV_SIGN_CONFIG') ?: __DIR__.'/private/config.php';
        if (!is_file($file)) throw new RuntimeException('Server configuration missing');
        $config = require $file;
    }
    return $config;
}
function respond(int $code, array $data): void {
    http_response_code($code);header('Content-Type: application/json; charset=utf-8');header('Cache-Control: no-store');
    echo json_encode($data, JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES);exit;
}
set_exception_handler(function(Throwable $error): void { error_log('polyv-sign: '.get_class($error));respond(500,['error'=>'Server error; check configuration, private-directory permissions and PHP cURL']); });
function body(): array {
    if (($_SERVER['REQUEST_METHOD']??'')!=='POST') respond(405,['error'=>'POST required']);
    $raw=file_get_contents('php://input', false, null, 0, 1048577);
    if ($raw===false || strlen($raw)>1048576) respond(413,['error'=>'Payload too large']);
    $data=json_decode($raw,true);
    if (!is_array($data)) respond(400,['error'=>'JSON object required']);
    return $data;
}
function authenticate(string $role): void {
    $expected=config()[$role.'_token'];
    $header=$_SERVER['HTTP_AUTHORIZATION']??'';
    if (!is_string($expected)||strlen($expected)<32||!hash_equals('Bearer '.$expected,$header)) respond(401,['error'=>'Unauthorized']);
}
function empty_state(): array {return ['seq'=>0,'events'=>[],'ids'=>[],'source'=>null,'last_callback'=>null,'last_increment'=>null,'last_fetch'=>0,'baseline'=>null,'cue_keys'=>[],'fetch_error'=>null];}
function callback_diagnostic(array $payload,string $result,int $httpCode):void {
    $meta=[];foreach(['channelId','source','language','isOriginal'] as $key){$value=$payload[$key]??null;$meta[$key]=is_scalar($value)?substr((string)$value,0,80):null;}
    state(function($s)use($meta,$result,$httpCode){
        $s['callback_attempts']=($s['callback_attempts']??0)+1;$s['last_callback_attempt']=time();
        $s['last_callback_result']=$result;$s['last_callback_http']=$httpCode;$s['last_callback_meta']=$meta;
        $s['received_sign_length']=is_string($_GET['sign']??null)?strlen($_GET['sign']):0;
        return $s;
    });
}
function state(callable $change): array {
    $path=config()['state_dir'];
    if (!is_dir($path)&&!mkdir($path,0700,true)&&!is_dir($path)) throw new RuntimeException('State directory not writable');
    $file=fopen($path.'/relay-state.php','c+');if(!$file||!flock($file,LOCK_EX))throw new RuntimeException('State lock failed');
    try {
        $prefix="<?php http_response_code(404); exit; ?>\n";
        rewind($file);$raw=stream_get_contents($file);
        $value=strncmp($raw,$prefix,strlen($prefix))===0 ? json_decode(substr($raw,strlen($prefix)),true) : null;
        if(!is_array($value))$value=empty_state();
        $value=$change($value);$encoded=$prefix.json_encode($value,JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES|JSON_THROW_ON_ERROR);
        rewind($file);fwrite($file,$encoded);ftruncate($file,strlen($encoded));fflush($file);
        return $value;
    } finally {flock($file,LOCK_UN);fclose($file);}
}
function append_event(array $s,string $id,string $text,string $source): array {
    if (in_array($id,$s['ids'],true))return $s;
    if(!preg_match('/^.{1,500}$/us',$text))throw new InvalidArgumentException('Caption length must be 1-500 characters');
    $s['seq']++;$s['events'][]=['seq'=>$s['seq'],'id'=>$id,'text'=>$text,'final'=>true,'created'=>microtime(true),'source'=>$source];
    $s['ids'][]=$id;$s['ids']=array_slice($s['ids'],-5000);$s['events']=array_slice($s['events'],-200);return $s;
}
function verified_callback(array $query,array $cfg,?float $now=null): bool {
    $ts=$query['timestamp']??'';$sign=$query['sign']??'';
    if(!is_string($ts)||!preg_match('/^\d{13}$/',$ts)||!is_string($sign))return false;
    if(abs(($now??microtime(true))*1000-(float)$ts)>900000)return false;
    return hash_equals(hash($cfg['callback_hash'],$cfg['app_secret'].$ts),strtolower($sign));
}
function allowed_srt(string $url,string $channel): bool {
    $p=parse_url($url);
    return is_array($p)&&($p['scheme']??'')==='https'&&($p['host']??'')==='polyv-chat.polyv.net'
        &&!isset($p['user'])&&!isset($p['pass'])&&(!isset($p['port'])||$p['port']===443)
        &&preg_match('~^/live/channel/srt/[^/]+/'.preg_quote($channel,'~').'/[A-Za-z0-9_/-]+\.srt$~',$p['path']??'')===1;
}
function fetch_srt(string $url): string {
    if(!allowed_srt($url,config()['channel_id']))throw new RuntimeException('SRT URL rejected');
    $curl=curl_init($url);$buffer='';
    curl_setopt_array($curl,[CURLOPT_FOLLOWLOCATION=>false,CURLOPT_CONNECTTIMEOUT=>3,CURLOPT_TIMEOUT=>6,CURLOPT_PROTOCOLS=>CURLPROTO_HTTPS,
        CURLOPT_SSL_VERIFYPEER=>true,CURLOPT_SSL_VERIFYHOST=>2,CURLOPT_HTTPHEADER=>['Cache-Control: no-cache'],
        CURLOPT_WRITEFUNCTION=>function($handle,string $chunk)use(&$buffer):int{if(strlen($buffer)+strlen($chunk)>2097152)return 0;$buffer.=$chunk;return strlen($chunk);}]);
    $ok=curl_exec($curl);$code=curl_getinfo($curl,CURLINFO_HTTP_CODE);curl_close($curl);
    if($ok===false||$code!==200)throw new RuntimeException('SRT fetch failed');return $buffer;
}
function parse_srt(string $text): array {
    $text=preg_replace('/^\xEF\xBB\xBF/','',$text);$text=str_replace(["\r\n","\r"],"\n",$text);$result=[];
    foreach(preg_split('/\n[ \t]*\n/',trim($text)) as $block){
        $lines=explode("\n",trim($block));$timeIndex=isset($lines[1])&&strpos($lines[1],'-->')!==false?1:0;
        if(!isset($lines[$timeIndex])||!preg_match('/^(\d{2,}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*(\d{2,}:\d{2}:\d{2}[,.]\d{3})/',$lines[$timeIndex],$m))continue;
        $content=trim(html_entity_decode(strip_tags(implode(' ',array_slice($lines,$timeIndex+1))),ENT_QUOTES|ENT_HTML5,'UTF-8'));
        if($content!==''&&preg_match('/^.{1,500}$/us',$content))$result[]=['key'=>$m[1].'|'.$m[2],'text'=>$content];
    }return $result;
}
function absorb_srt(array $s,string $url,array $cues): array {
    $keys=array_column($cues,'key');
    if($s['baseline']!==$url){$s['baseline']=$url;$s['cue_keys']=$keys;return $s;}
    foreach($cues as $cue)if(!in_array($cue['key'],$s['cue_keys'],true)){
        $s=append_event($s,'srt:'.hash('sha256',$url.'|'.$cue['key']),$cue['text'],'srt-increment');$s['last_increment']=time();
    }
    $s['cue_keys']=array_slice(array_unique(array_merge($s['cue_keys'],$keys)),-10000);return $s;
}
function refresh_srt(): void {
    $s=state(function($s){return $s;});
    if(!$s['source']||microtime(true)-$s['last_fetch']<1)return;
    $lock=fopen(config()['state_dir'].'/refresh-lock.php','c+');
    if(!$lock||!flock($lock,LOCK_EX|LOCK_NB)){if($lock)fclose($lock);return;}
    try{
        $url=$s['source']['url'];$cues=parse_srt(fetch_srt($url));
        state(function($s)use($url,$cues){if(($s['source']['url']??null)===$url)$s=absorb_srt($s,$url,$cues);$s['last_fetch']=microtime(true);$s['fetch_error']=null;return $s;});
    }catch(Throwable $e){state(function($s){$s['last_fetch']=microtime(true);$s['fetch_error']='SRT download/parse failed; inspect source and cURL';return $s;});}
    finally{flock($lock,LOCK_UN);fclose($lock);}
}
