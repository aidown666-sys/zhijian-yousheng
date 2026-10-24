# 保利威字幕与采集

## 观看页路径（当前首选）

控制台配置普通游客可看的 https://账号.live.plvideo.net/watch/频道号，保存在本机 watch-config.json，不提交。通过正常观看接口取得游客会话和 chatToken，再连接 Socket.IO/Engine.IO 字幕消息。不推导 token，不绕过登录、付费或密码权限。

中文片段根据 UTF-16 replaceIndex 合并，定稿按直播场次和字幕编号去重，转入本机 /api/captions。主程序管理接收器，断线重连并恢复异常退出的子进程。不要重复启动多个接收器。

诊断页依次检查：接收器心跳和 Socket 登录确认；字幕计数和最近定稿；queued/unsupported 转换结果及缺词；输出窗口心跳和模型加载。客户端显示字幕不能证明本机已接入。

## PHP 回调中转（备用）

server/ 需要 PHP 7.4+、cURL、HTTPS 及可写私有状态目录。将 config.example.php 复制为 server/private/config.php 并填写配置，禁止 Web 访问 private 目录，真实配置不提交。

callback.php 验签并记录官方 SRT 地址，poll.php 拉取 SRT 增量。这不是逐条字幕定稿回调；直播中能否持续增量更新须核对实际服务行为。

本机复制 local-bridge.example.json 为 local-bridge.json，填写 poll.php URL 和 consumer token。bridge.py 主动 HTTPS 轮询，再发到 127.0.0.1:8877/api/captions，所以公网服务器无需直接连接用户电脑。首次连接只建立当前位置基线。

configure.php 用 admin token 查询或修改官方回调。ingest.php 是 producer token 保护的通用入口，不是保利威原生回调格式。

## 采集

open-capture-window.cmd 打开独立窗口，保利威添加窗口采集，绿幕通过色键扣除；控制页也支持背景图。背景仅在本机处理。OBS 可直接使用 /output 浏览器源。当前没有虚拟摄像头设备。
