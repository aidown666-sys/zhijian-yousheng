<?php
declare(strict_types=1);require __DIR__.'/common.php';authenticate('producer');$p=body();
if((string)($p['channelId']??'')!==config()['channel_id'])respond(403,['error'=>'Wrong channel']);
if(($p['final']??null)!==true)respond(200,['status'=>'partial_ignored']);
if(!is_string($p['id']??null)||strlen($p['id'])>200||$p['id']===''||!is_string($p['text']??null))respond(400,['error'=>'id/text required']);
$text=trim($p['text']);if(!preg_match('/^.{1,500}$/us',$text))respond(400,['error'=>'Invalid caption length']);
$s=state(function($s)use($p,$text){return append_event($s,'push:'.$p['id'],$text,'authenticated-text-push');});
respond(200,['status'=>'accepted','latest'=>$s['seq']]);
