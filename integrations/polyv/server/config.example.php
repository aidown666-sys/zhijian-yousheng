<?php
// Copy to private/config.php. Never commit real credentials.
return [
    'app_id' => 'YOUR_APP_ID',
    'app_secret' => 'YOUR_APP_SECRET',
    'channel_id' => 'YOUR_CHANNEL',
    'callback_url' => 'https://YOUR_DOMAIN/polyv/callback.php',
    'callback_hash' => 'md5',
    'producer_token' => 'REPLACE_WITH_SEPARATE_32_OR_MORE_RANDOM_CHARACTERS',
    'consumer_token' => 'REPLACE_WITH_SEPARATE_32_OR_MORE_RANDOM_CHARACTERS',
    'admin_token' => 'REPLACE_WITH_SEPARATE_32_OR_MORE_RANDOM_CHARACTERS',
    'state_dir' => __DIR__,
];
