# 敏感配置

不要提交 .env、integrations/polyv/local-bridge.json、watch-config.json、server/private/、含配置的部署 ZIP、直播字幕日志或 runtime/。这些本机文件已通过 .gitignore 排除，仓库只保留不含真实凭据的 example 配置。

模板均为占位符。appSecret 只放 PHP 服务端；producer、consumer、admin token 应分别使用不少于 32 字符的随机值。本地服务只监听回环地址，不直接暴露公网。PHP 部署禁止 Web 访问 private 目录。

动作数据含 pickle 编码，仅使用清单中可信且校验通过的文件，不加载陌生上传数据。私有备份不表示获得商用或公开再分发授权，公开前须重新审核。

## 提交前检查

```powershell
python tools/audit_secrets.py --history --report outputs/security-audit/report.json
```

检查器对已跟踪文件、Git 暂存区、当前可达的 Git 历史和忽略规则进行检查；从本机已忽略的生产配置读取已知 appId、appSecret 和令牌作精确比对，输出只包含字段名、文件路径和检查结果，不输出凭据。没有本机生产配置的电脑仍可检查硬编码字段、常见令牌和私钥特征，但不能比对本机已知值。

大型工作区资产会流式检查已知值，Git 历史检查包含其中保存的 LFS 指针。它不是对外部 LFS 服务、第三方 Fork、GitHub 缓存或图片中的文字的全面扫描。若发现真实凭据已公开，应先在保利威控制台撤销或轮换，再清理 Git 历史；仅从最新文件删除不能使已泄露凭据失效。
