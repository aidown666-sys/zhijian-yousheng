<?php
declare(strict_types=1);
if(PHP_SAPI!=='cli'){http_response_code(404);exit;}
require __DIR__.'/common.php';$cfg=config();$enable=in_array('--enable-callback',$argv,true);
$params=['appId'=>$cfg['app_id'],'channelId'=>$cfg['channel_id'],'timestamp'=>(string)(int)(microtime(true)*1000)];ksort($params,SORT_STRING);
$str=$cfg['app_secret'];foreach($params as $k=>$v)$str.=$k.$v;$params['sign']=strtoupper(md5($str.$cfg['app_secret']));
$endpoint='https://api.polyv.net/live/v4/channel/subtitle/config/'.($enable?'update':'get');
$curl=curl_init($endpoint.'?'.http_build_query($params));curl_setopt_array($curl,[CURLOPT_RETURNTRANSFER=>true,CURLOPT_TIMEOUT=>15,CURLOPT_SSL_VERIFYPEER=>true,CURLOPT_SSL_VERIFYHOST=>2]);
if($enable)curl_setopt_array($curl,[CURLOPT_POST=>true,CURLOPT_HTTPHEADER=>['Content-Type: application/json'],CURLOPT_POSTFIELDS=>json_encode(['channelId'=>(int)$cfg['channel_id'],'subtitleCallbackEnabled'=>'Y','subtitleCallbackUrl'=>$cfg['callback_url']])]);
$result=curl_exec($curl);if($result===false){fwrite(STDERR,"API transport failed; check PHP cURL/CA configuration\n");exit(1);}echo $result,"\n";
