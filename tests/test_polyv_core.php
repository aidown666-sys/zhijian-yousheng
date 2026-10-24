<?php
require dirname(__DIR__).'/integrations/polyv/server/common.php';
function check($ok,string $label):void{if(!$ok){fwrite(STDERR,'FAILED: '.$label."\n");exit(1);}}
$cfg=['app_secret'=>'unit-test-secret','callback_hash'=>'md5'];$ts='1700000000000';
check(verified_callback(['timestamp'=>$ts,'sign'=>md5($cfg['app_secret'].$ts)],$cfg,1700000000),'valid signature');
check(!verified_callback(['timestamp'=>$ts,'sign'=>str_repeat('0',32)],$cfg,1700000000),'bad signature rejected');
check(!verified_callback(['timestamp'=>$ts,'sign'=>md5($cfg['app_secret'].$ts)],$cfg,1700009000),'expired timestamp');
$url='https://polyv-chat.polyv.net/live/channel/srt/test/8662629/session/Chinese.srt';
check(allowed_srt($url,'8662629'),'official channel SRT');
check(!allowed_srt('https://127.0.0.1/private.srt','8662629'),'private destination rejected');
check(!allowed_srt(str_replace('8662629','1',$url),'8662629'),'other channel rejected');
$one=parse_srt("1\r\n00:00:01,000 --> 00:00:02,000\r\n今天我去学校\r\n\r\n");
check(count($one)===1&&$one[0]['text']==='今天我去学校','SRT parsing');
$s=absorb_srt(empty_state(),$url,$one);check($s['seq']===0,'initial file is baseline, no replay');
$two=array_merge($one,parse_srt("2\n00:00:03,000 --> 00:00:04,000\n<b>欢迎</b>\n"));
$s=absorb_srt($s,$url,$two);check($s['seq']===1&&$s['events'][0]['text']==='欢迎','new cue delivered');
$s=absorb_srt($s,$url,$two);check($s['seq']===1,'SRT retries deduplicated');
$s=append_event($s,'push:test','今天我去学校','test');$s=append_event($s,'push:test','今天我去学校','test');check($s['seq']===2,'text push retries deduplicated');
echo "11 PHP relay checks passed\n";
