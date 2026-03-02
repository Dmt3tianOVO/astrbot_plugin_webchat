# Minimal WebChat Client

This is the smallest browser demo for `astrbot_plugin_webchat`.

## Run

From this directory, run a static server:

```powershell
cd AstrBot_Plugin/AstrBot/data/plugins/astrbot_plugin_webchat/examples/minimal_webchat_client
python -m http.server <your_frontend_port>
```

Then open:

- `http://localhost:<your_frontend_port>`

Example:

```powershell
python -m http.server 1234
```

The page lets you set:

- API base URL (for example `http://127.0.0.1:6186`)
- endpoint path (for example `/api/webchat`)
- API key (optional, if plugin `api_key` is configured)

## Required plugin config

Make sure plugin `allowed_origins` includes this page origin:

- `http://localhost:<your_frontend_port>`

Example:

- `http://localhost:1234`

Recommended plugin config example:

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

If you change frontend port or endpoint path, remember to update:

- browser page URL origin
- plugin `allowed_origins`
- plugin `endpoint_path`

## Test flow

1. Start AstrBot and ensure plugin logs show API started.
2. Open `http://localhost:1234` (or your chosen frontend port).
3. Fill API base URL and endpoint path to match plugin config.
4. Enter message and click **Send**.
5. Confirm response contains `reply`.
