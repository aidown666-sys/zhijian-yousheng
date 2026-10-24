# 敏感配置

仓库保持私有。不要提交 .env、integrations/polyv/local-bridge.json、watch-config.json、server/private/、含配置的部署 ZIP、直播字幕日志或 runtime/。

模板均为占位符。appSecret 只放 PHP 服务端；producer、consumer、admin token 应分别使用不少于 32 字符的随机值。本地服务只监听回环地址，不直接暴露公网。PHP 部署禁止 Web 访问 private 目录。

动作数据含 pickle 编码，仅使用清单中可信且校验通过的文件，不加载陌生上传数据。私有备份不表示获得商用或公开再分发授权，公开前须重新审核。
