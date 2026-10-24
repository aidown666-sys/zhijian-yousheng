<?php
declare(strict_types=1);require __DIR__.'/common.php';
$payload=body();$cfg=config();
if(!verified_callback($_GET,$cfg)){callback_diagnostic($payload,'signature_or_timestamp_rejected',403);respond(403,['error'=>'Invalid callback signature or timestamp']);}
if((string)($payload['channelId']??'')!==$cfg['channel_id']){callback_diagnostic($payload,'wrong_channel',403);respond(403,['error'=>'Wrong channel']);}
if(($payload['source']??'')!=='chatRealtimeSrt'||($payload['language']??'')!=='Chinese'||($payload['isOriginal']??'')!=='Y'){callback_diagnostic($payload,'filtered_non_original_chinese_live_subtitle',200);respond(200,['status'=>'ignored_non_original_chinese_live_subtitle']);}
$url=$payload['srtUrl']??'';
if(!is_string($url)||!allowed_srt($url,$cfg['channel_id'])){callback_diagnostic($payload,'unsupported_srt_url',400);respond(400,['error'=>'Unsupported SRT URL; inspect actual callback format']);}
callback_diagnostic($payload,'source_registered',200);
state(function($s)use($payload,$url){$s['last_callback']=time();$s['source']=['url'=>$url,'id'=>(string)($payload['id']??''),'file_id'=>(string)($payload['fileId']??'')];return $s;});
respond(200,['status'=>'source_registered','realtime_delivery'=>'Not guaranteed; SRT increments must be observed during a live test']);
