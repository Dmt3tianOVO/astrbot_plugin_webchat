[中文](./README.md) | [English](./README.en.md)
# astrbot_plugin_webchat

A lightweight AstrBot plugin that exposes an HTTP endpoint:

- `POST /api/webchat`
- default bind: `0.0.0.0:6186`
- supports configurable host/port/path and browser origin allow-list

The endpoint accepts a web chat payload, calls AstrBot's configured chat provider, and persists conversation history through `conversation_manager`.

## Quick start tutorial

1. Install this plugin from local folder or plugin repo.
2. Configure plugin settings in AstrBot Dashboard (recommended):
   - `host`: `0.0.0.0`
   - `port`: `6186`
   - `endpoint_path`: `/api/webchat`
   - `allowed_origins`: `http://localhost:<your_frontend_port>`
3. Restart AstrBot (or reload plugin), then verify startup logs include:
   - `API started at http://<host>:<port><path>`
4. Run your web page on any local port (for example `http://localhost:1234`) and call `POST http://127.0.0.1:6186/api/webchat`.
5. Confirm response JSON contains `reply`.


A minimal runnable frontend sample is provided in:

- `examples/minimal_webchat_client/`


## Request payload

```json
{
  "sessionId": "optional-session-id",
  "userId": "optional-user-id",
  "username": "optional-username",
  "message": "hello"
}
```

`session_id` / `user_id` (snake_case) are also supported.

## Response payload

```json
{
  "reply": "model output text"
}
```

Possible errors:

- `400 {"error": "invalid_json"}`
- `400 {"error": "invalid_payload"}`
- `403 {"error": "forbidden_origin"}`
- `500 {"error": "llm_call_failed", "detail": "..."}`


## Plugin config

You can configure runtime behavior in plugin config:

- `host` (default: `0.0.0.0`)
- `port` (default: `6186`)
- `endpoint_path` (default: `/api/webchat`)
- `allowed_origins` (default: `*`)
  - supports comma-separated string or list
  - example: `http://localhost:1234,http://127.0.0.1:1234`
  - you can replace `1234` with any frontend port you use


Example:

```json
{
  "host": "0.0.0.0",
  "port": 6186,
  "endpoint_path": "/api/webchat",
  "allowed_origins": "http://localhost:1234"
}
```

## Notes

- The plugin starts the API server after AstrBot is loaded.
- The plugin stops and cleans up server resources on terminate.
- If `persona_id` is configured, its `system_prompt` will be merged into the final LLM prompt.
- If `allowed_origins` is not `*`, browser requests from other origins are rejected with `403 forbidden_origin`.


