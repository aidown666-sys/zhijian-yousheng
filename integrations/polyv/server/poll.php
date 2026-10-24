<?php
declare(strict_types=1);require __DIR__.'/common.php';authenticate('consumer');
if(($_SERVER['REQUEST_METHOD']??'')!=='GET')respond(405,['error'=>'GET required']);
$after=filter_var($_GET['after']??'0',FILTER_VALIDATE_INT);if($after===false||$after<0)respond(400,['error'=>'Invalid cursor']);
refresh_srt();$s=state(function($s){return $s;});
$items=array_values(array_filter($s['events'],function($e)use($after){return $e['seq']>$after;}));
respond(200,['latest'=>$s['seq'],'events'=>array_slice($items,0,30),'status'=>[
    'channel_id'=>config()['channel_id'],'last_callback'=>$s['last_callback'],'last_increment'=>$s['last_increment'],
    'has_srt_source'=>(bool)$s['source'],'baseline_set'=>(bool)$s['baseline'],'fetch_error'=>$s['fetch_error'],
    'callback_attempts'=>$s['callback_attempts']??null,'last_callback_attempt'=>$s['last_callback_attempt']??null,
    'last_callback_result'=>$s['last_callback_result']??null,'last_callback_http'=>$s['last_callback_http']??null,
    'last_callback_meta'=>$s['last_callback_meta']??null,'received_sign_length'=>$s['received_sign_length']??null,
    'diagnostic_version'=>2,
    'note'=>'Official callback carries SRT URL, not per-sentence text. No increment means no live caption delivery.']]);
