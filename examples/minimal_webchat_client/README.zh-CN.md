# 最小 WebChat 前端示例

这是 `astrbot_plugin_webchat` 的最小浏览器调用示例。

## 运行方式

在当前目录启动静态服务器：

```powershell
cd AstrBot_Plugin/AstrBot/data/plugins/astrbot_plugin_webchat/examples/minimal_webchat_client
python -m http.server <你的前端端口>
```

打开：

- `http://localhost:<你的前端端口>`

例如：

```powershell
python -m http.server 1234
```

页面里可以自行填写：

- API Base URL（例如 `http://127.0.0.1:6186`）
- Endpoint Path（例如 `/api/webchat`）

## 插件配置要求

确保插件配置中的 `allowed_origins` 包含当前页面来源：

- `http://localhost:<你的前端端口>`

配置示例：

```json
{
  "host": "0.0.0.0",
  "port": 6186,
  "endpoint_path": "/api/webchat",
  "allowed_origins": "http://localhost:1234"
}
```

如果你改了前端端口或接口路径，请同步修改：

- 浏览器页面来源（Origin）
- 插件 `allowed_origins`
- 插件 `endpoint_path`

## 测试流程

1. 启动 AstrBot，确认插件日志出现 API 启动信息。
2. 打开示例页面。
3. 填写 API Base URL 与 Endpoint Path。
4. 输入消息并点击 **Send**。
5. 返回结果中包含 `reply` 即表示联调成功。
