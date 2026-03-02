# astrbot_plugin_webchat

这是一个轻量的 AstrBot 插件，用于暴露 HTTP 接口：

- `POST /api/webchat`
- 默认监听：`0.0.0.0:6186`
- 支持配置 host/port/path、浏览器来源（Origin）白名单，以及可选 API Key 鉴权

该接口会接收网页聊天消息，调用 AstrBot 当前配置的聊天模型提供方，并通过 `conversation_manager` 持久化会话。

## 快速开始

1. 从本地目录或插件仓库安装本插件。
2. 在 AstrBot Dashboard 中配置插件参数（推荐）：
   - `host`: `0.0.0.0`
   - `port`: `6186`
   - `endpoint_path`: `/api/webchat`
   - `allowed_origins`: `http://localhost:<你的前端端口>`
   - `api_key`: `your-strong-key`（生产环境强烈建议配置）
   - `history_turns`: `8`（多轮上下文保留轮数）
3. 重启 AstrBot（或重载插件），确认日志包含：
   - `API started at http://<host>:<port><path>`
4. 在任意本地端口启动前端页面（例如 `http://localhost:1234`），并向 `POST http://127.0.0.1:6186/api/webchat` 发请求。
5. 确认返回 JSON 中包含 `reply`。

最小可运行前端示例位于：

- `examples/minimal_webchat_client/`

## 请求体

```json
{
  "sessionId": "optional-session-id",
  "userId": "optional-user-id",
  "username": "optional-username",
  "message": "hello"
}
```

也支持 `session_id` / `user_id`（snake_case）。

## 响应体

```json
{
  "reply": "model output text"
}
```

## 常见错误

- `400 {"error": "invalid_json"}`
- `400 {"error": "invalid_payload"}`
- `401 {"error": "unauthorized"}`
- `403 {"error": "forbidden_origin"}`
- `500 {"error": "llm_call_failed", "detail": "..."}`

## 插件配置项

- `host`（默认：`0.0.0.0`）
- `port`（默认：`6186`）
- `endpoint_path`（默认：`/api/webchat`）
- `allowed_origins`（默认：`*`）
  - 支持逗号分隔字符串或列表
  - 示例：`http://localhost:1234,http://127.0.0.1:1234`
  - `1234` 可替换为你实际前端端口
- `api_key`（默认：空）
  - 配置后启用鉴权
  - 支持请求头：`X-API-Key: <key>` 或 `Authorization: Bearer <key>`
- `history_turns`（默认：`8`）
  - 每次请求带入最近 N 轮历史上下文，提升多轮对话连续性

配置示例：

```json
{
  "host": "0.0.0.0",
  "port": 6186,
  "endpoint_path": "/api/webchat",
  "allowed_origins": "http://localhost:1234",
  "api_key": "your-strong-key",
  "history_turns": 8
}
```

## 说明

- AstrBot 启动后，插件会自动启动 API 服务。
- 插件停用/卸载时，会自动释放服务资源。
- 如果配置了 `persona_id`，会将对应 `system_prompt` 合并到最终提示词。
- 插件会携带最近历史上下文（`history_turns`）以支持多轮对话。
- 当 `allowed_origins` 不是 `*` 时，非白名单来源的浏览器请求会返回 `403 forbidden_origin`。
- 仅靠 CORS 不能防止脚本直连，建议在生产环境务必配置 `api_key`。
