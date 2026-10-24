# 架构与开发

```text
输入文本 / 保利威观看页字幕 / PHP 中转拉取
  → POST /api/captions（定稿、去重）
  → 完整句检索 / 词片段拼接
  → 本地事件队列
  → Three.js / VRM 参考骨骼
  → 用户模型重定向
  → 独立窗口 / OBS 浏览器源
```

live_server.py 使用标准库 HTTP 服务，依赖 NumPy、LMDB、Pillow、websocket-client。默认 127.0.0.1:8877。浏览器依赖位于 web/vendor/，无需运行时 CDN。

| 接口 | 用途 |
| --- | --- |
| POST /api/captions | JSON {"id":"demo-001","text":"他今年四岁。","final":true}；定稿触发，相同 id 去重 |
| GET /api/events | 输出页拉取事件 |
| GET /api/samples | 已收录示例 |
| GET /api/diagnostics | 接收与转换结果 |
| GET /api/bridge-status | 字幕接收器状态 |
| GET/POST /api/background | 自定义背景和开关 |
| GET/POST /api/motion-settings | 片段演示 / 严格模式 |
| POST /api/output-heartbeat | 输出窗口状态 |
| /diagnostics | 可视化排障 |
| /output | 采集页面 |

具体请求参数以 live_server.py 为准。输出页待播上限 8 条，丢弃超过 15 秒的积压。

标准手部版使用用户身体及 pixiv 示例手部网格和权重。隐藏的 VRM 参考骨骼接收动漫模型同样的驱动，经 standard-hand-alignment.json 校准世界旋转。模型骨轴、静止姿态和权重不同，不能直接套用局部旋转。

/output?model=SignHuman_Final&review=1 可查看固定动作帧，不订阅直播字幕。数学和网格检查不等价于手语语义或审美质量认证。

历史建模工具部分依赖原工作环境；当前人物修改入口见 ASSETS.md。提交前运行 Python/Node 测试与资产清单校验。
