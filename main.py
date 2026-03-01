"""WebChat API plugin for AstrBot.

This plugin exposes an HTTP endpoint (`POST /api/webchat`) that forwards
incoming user messages to AstrBot's configured LLM provider and stores
conversation history through `conversation_manager`.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from aiohttp import web

from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import filter
from astrbot.api.star import Context, Star, register
from astrbot.core.agent.message import (
    AssistantMessageSegment,
    TextPart,
    UserMessageSegment,
)


@dataclass
class WebChatRequest:
    """Normalized request payload for `/api/webchat`."""

    session_id: str
    user_id: str
    username: str
    message: str


@register("webchat_api", "CodeHub", "Expose /api/webchat for CodeHub web chat", "1.0.0")
class WebChatApiPlugin(Star):
    """AstrBot plugin that hosts a lightweight aiohttp WebChat API server."""

    def __init__(
        self,
        context: Context,
        config: AstrBotConfig | None = None,
    ) -> None:
        """Initialize plugin runtime state and web server handles."""
        super().__init__(context)
        self.config = config
        self._runner: web.AppRunner | None = None
        self._site: web.TCPSite | None = None
        self._lock = asyncio.Lock()

        self._host = str(self._config_get("host", "0.0.0.0")).strip() or "0.0.0.0"
        self._port = self._parse_port(self._config_get("port"), default=6186)
        self._endpoint_path = self._normalize_endpoint_path(
            self._config_get("endpoint_path")
        )
        self._allowed_origins = self._parse_allowed_origins(
            self._config_get("allowed_origins")
        )

    def _config_get(self, key: str, default: Any = None) -> Any:
        """Safely read plugin config for compatibility across loader versions."""
        if self.config is None:
            return default

        getter = getattr(self.config, "get", None)
        if callable(getter):
            return getter(key, default)

        return default

    @filter.on_astrbot_loaded()
    async def on_astrbot_loaded(self) -> None:
        """Start the API server after AstrBot finishes startup."""
        await self._start_server()

    async def terminate(self) -> None:
        """Stop the API server during plugin unload/disable."""
        await self._stop_server()

    async def _start_server(self) -> None:
        """Create and start the aiohttp server exactly once."""
        async with self._lock:
            if self._runner:
                return

            app = web.Application()
            app.router.add_post(self._endpoint_path, self._handle_webchat)
            app.router.add_options(self._endpoint_path, self._handle_preflight)
            self._runner = web.AppRunner(app)
            await self._runner.setup()
            self._site = web.TCPSite(self._runner, self._host, self._port)
            await self._site.start()
            logger.info(
                "[WebChat] API started at http://%s:%s%s",
                self._host,
                self._port,
                self._endpoint_path,
            )
            logger.info(
                "[WebChat] allowed_origins=%s",
                ", ".join(sorted(self._allowed_origins)),
            )

    async def _stop_server(self) -> None:
        """Release aiohttp resources if the server is running."""
        async with self._lock:
            if not self._runner:
                return
            await self._runner.cleanup()
            self._runner = None
            self._site = None
            logger.info("[WebChat] API stopped")

    async def _handle_preflight(self, request: web.Request) -> web.Response:
        """Handle browser CORS preflight requests."""
        origin = self._extract_origin(request)
        if not self._is_origin_allowed(origin):
            return self._json_response(
                {"error": "forbidden_origin"},
                status=403,
                origin=origin,
            )
        return web.Response(status=204, headers=self._build_cors_headers(origin))

    async def _handle_webchat(self, request: web.Request) -> web.Response:
        """Handle incoming `/api/webchat` requests and return model output."""
        origin = self._extract_origin(request)
        if not self._is_origin_allowed(origin):
            logger.warning(
                "[WebChat] Blocked request from origin: %s", origin or "<none>"
            )
            return self._json_response(
                {"error": "forbidden_origin"},
                status=403,
                origin=origin,
            )

        logger.info("[WebChat] Request received from: %s", request.remote)
        try:
            payload = await request.json()
        except Exception:
            return self._json_response(
                {"error": "invalid_json"},
                status=400,
                origin=origin,
            )

        data = self._parse_request(payload)
        if not data:
            return self._json_response(
                {"error": "invalid_payload"},
                status=400,
                origin=origin,
            )

        logger.info(
            "[WebChat] payload session=%s user=%s message=%s",
            data.session_id,
            data.username,
            data.message,
        )

        try:
            reply = await self._generate_reply(data)
        except Exception as error:
            logger.exception("[WebChat] LLM call failed")
            return self._json_response(
                {"error": "llm_call_failed", "detail": str(error)},
                status=500,
                origin=origin,
            )

        return self._json_response({"reply": reply}, origin=origin)

    def _json_response(
        self,
        payload: dict[str, Any],
        *,
        status: int = 200,
        origin: str | None = None,
    ) -> web.Response:
        """Create a JSON response with proper CORS headers."""
        return web.json_response(
            payload,
            status=status,
            headers=self._build_cors_headers(origin),
        )

    def _build_cors_headers(self, origin: str | None) -> dict[str, str]:
        """Build CORS headers based on current allow-list configuration."""
        headers = {
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
        }

        if "*" in self._allowed_origins:
            headers["Access-Control-Allow-Origin"] = "*"
            return headers

        if origin and origin in self._allowed_origins:
            headers["Access-Control-Allow-Origin"] = origin
            headers["Vary"] = "Origin"

        return headers

    def _extract_origin(self, request: web.Request) -> str | None:
        """Extract request origin from `Origin` or `Referer` headers."""
        origin = (request.headers.get("Origin") or "").strip()
        if origin:
            return origin

        referer = (request.headers.get("Referer") or "").strip()
        if not referer:
            return None

        parsed = urlparse(referer)
        if not parsed.scheme or not parsed.netloc:
            return None
        return f"{parsed.scheme}://{parsed.netloc}"

    def _is_origin_allowed(self, origin: str | None) -> bool:
        """Check whether request origin is allowed to access this API."""
        if "*" in self._allowed_origins:
            return True

        # Non-browser clients may not send Origin/Referer headers.
        if origin is None:
            return True

        return origin in self._allowed_origins

    def _normalize_endpoint_path(self, raw_path: Any) -> str:
        """Normalize endpoint path and ensure it starts with '/'."""
        path = str(raw_path or "/api/webchat").strip() or "/api/webchat"
        if not path.startswith("/"):
            path = f"/{path}"
        return path

    def _parse_port(self, raw_port: Any, *, default: int) -> int:
        """Parse and validate TCP port from plugin config."""
        if raw_port is None:
            return default

        try:
            parsed = int(raw_port)
        except (TypeError, ValueError):
            logger.warning(
                "[WebChat] Invalid port=%s, fallback to %s",
                raw_port,
                default,
            )
            return default

        if not 1 <= parsed <= 65535:
            logger.warning(
                "[WebChat] Out-of-range port=%s, fallback to %s",
                raw_port,
                default,
            )
            return default

        return parsed

    def _parse_allowed_origins(self, raw_origins: Any) -> set[str]:
        """Parse allow-list from list/tuple or comma-separated string.

        Examples:
            - "*"
            - "http://localhost:1234,http://127.0.0.1:1234"
            - ["http://localhost:1234"]
        """
        if raw_origins is None:
            return {"*"}

        parsed_origins: set[str] = set()

        if isinstance(raw_origins, str):
            candidates = [item.strip() for item in raw_origins.split(",")]
        elif isinstance(raw_origins, (list, tuple, set)):
            candidates = [str(item).strip() for item in raw_origins]
        else:
            logger.warning(
                "[WebChat] Invalid allowed_origins type=%s, fallback to '*'",
                type(raw_origins).__name__,
            )
            return {"*"}

        for origin in candidates:
            if origin:
                parsed_origins.add(origin)

        return parsed_origins or {"*"}

    def _parse_request(self, payload: dict[str, Any]) -> WebChatRequest | None:
        """Validate and normalize payload fields from camel/snake case keys."""
        message = str(payload.get("message") or "").strip()
        if not message:
            return None

        session_id = str(
            payload.get("sessionId") or payload.get("session_id") or "webchat"
        )
        user_id = str(payload.get("userId") or payload.get("user_id") or "")
        username = str(payload.get("username") or "WebUser")

        return WebChatRequest(
            session_id=session_id,
            user_id=user_id,
            username=username,
            message=message,
        )

    async def _get_persona(self) -> tuple[str | None, str | None]:
        """Read configured persona and return `(persona_id, system_prompt)`."""
        persona_id = (self._config_get("persona_id") or "").strip()
        if not persona_id:
            return None, None

        try:
            persona = await self.context.persona_manager.get_persona(persona_id)
            system_prompt = (getattr(persona, "system_prompt", "") or "").strip()
            return persona_id, system_prompt or None
        except Exception:
            logger.warning("[WebChat] persona_id does not exist: %s", persona_id)
            return None, None

    async def _generate_reply(self, data: WebChatRequest) -> str:
        """Generate reply text and persist conversation history."""
        unified_origin = f"webchat:private:{data.session_id}"
        provider_id = await self.context.get_current_chat_provider_id(
            umo=unified_origin
        )
        if not provider_id:
            raise RuntimeError("chat_provider_not_configured")

        persona_id, persona_system_prompt = await self._get_persona()
        logger.info(
            "[WebChat] Using persona_id=%s provider_id=%s",
            persona_id or "<default>",
            provider_id,
        )

        identity_lock = (
            'You must always answer as "小智".'
            "Never claim to be DeepSeek, an AI assistant, an LLM, or a bot."
            'If asked "who are you", answer exactly: "我是小智".'
        )
        if persona_system_prompt:
            merged_prompt = (
                f"{persona_system_prompt}\n\n"
                f"[Identity Rules]{identity_lock}\n\n"
                f"User message: {data.message}"
            )
        else:
            merged_prompt = (
                f"[Identity Rules]{identity_lock}\n\nUser message: {data.message}"
            )

        llm_resp = await self.context.llm_generate(
            chat_provider_id=provider_id,
            prompt=merged_prompt,
            persona_id=persona_id,
        )

        reply_text = (llm_resp.completion_text or "").strip()

        try:
            conv_mgr = self.context.conversation_manager
            curr_cid = await conv_mgr.get_curr_conversation_id(unified_origin)
            if not curr_cid:
                curr_cid = await conv_mgr.new_conversation(
                    unified_origin,
                    platform_id="webchat",
                    title=data.username,
                )

            await conv_mgr.add_message_pair(
                cid=curr_cid,
                user_message=UserMessageSegment(content=[TextPart(text=data.message)]),
                assistant_message=AssistantMessageSegment(
                    content=[TextPart(text=reply_text)]
                ),
            )
        except Exception:
            logger.exception("[WebChat] Failed to persist conversation")

        return reply_text
