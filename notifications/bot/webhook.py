"""ASGI entry point for the Telegram bot service (Stories 9.1 + 9.6).

The systemd unit `iwallet-bot.service` runs:

    uvicorn notifications.bot.webhook:app --host 127.0.0.1 --port 8011

We do NOT just expose Django's ASGI app because the webhook lives *outside*
`/app/*` (Telegram POSTs from telegram.org IPs and never sends initData), and
the project's middleware stack rejects anything `/app/*` without auth.

Two paths handled here:

    POST /bot/webhook/<secret>/        — receives Telegram Updates
    GET  /healthz                       — uvicorn liveness check

Everything else is delegated to Django so `uvicorn notifications.bot.webhook:app`
can also serve `/app/*` if Eric chooses to fold the two services together in
v1.1. For now the systemd reverse-proxy split (Caddy → 8000 for /app, → 8011
for /bot) is the recommended deployment.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

# Django must be set up *before* importing any model-touching modules; the
# ASGI bot service starts independently of the WSGI Django process.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "iwallet.settings")

import django  # noqa: E402

django.setup()

from asgiref.sync import sync_to_async  # noqa: E402
from django.conf import settings  # noqa: E402
from django.core.asgi import get_asgi_application  # noqa: E402

from notifications.bot.handlers import (  # noqa: E402
    handle_callback_query,
    handle_message_update,
)

logger = logging.getLogger(__name__)

_django_app = get_asgi_application()

WEBHOOK_PATH_PREFIX = "/bot/webhook/"


async def _read_body(receive) -> bytes:
    """Drain the ASGI receive channel for the full request body."""
    body = b""
    more = True
    while more:
        message = await receive()
        if message["type"] != "http.request":
            continue
        body += message.get("body", b"")
        more = message.get("more_body", False)
    return body


async def _send_json(send, status: int, payload: dict[str, Any]) -> None:
    body = json.dumps(payload).encode("utf-8")
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode("ascii")),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})


def _secret_from_path(path: str) -> str | None:
    """Strip the prefix and return the secret token, or None if path is wrong shape."""
    if not path.startswith(WEBHOOK_PATH_PREFIX):
        return None
    rest = path[len(WEBHOOK_PATH_PREFIX) :]
    # Allow optional trailing slash: `/bot/webhook/<secret>/` or `/bot/webhook/<secret>`.
    return rest.rstrip("/")


async def handle_webhook(scope, receive, send) -> None:
    """ASGI handler for `POST /bot/webhook/<secret>/`."""
    if scope["method"] != "POST":
        await _send_json(send, 405, {"error": "method_not_allowed"})
        return

    expected_secret = getattr(settings, "TELEGRAM_WEBHOOK_SECRET", "")
    if not expected_secret:
        logger.error("TELEGRAM_WEBHOOK_SECRET not configured — refusing webhook traffic")
        await _send_json(send, 503, {"error": "webhook_secret_not_configured"})
        return

    path_secret = _secret_from_path(scope["path"])
    # Telegram can additionally include the secret in `X-Telegram-Bot-Api-Secret-Token`
    # when configured via setWebhook(secret_token=...). Accept either path or header
    # to support both rollout patterns; require at least one to match.
    header_secret = ""
    for raw_name, raw_value in scope.get("headers", []):
        if raw_name == b"x-telegram-bot-api-secret-token":
            header_secret = raw_value.decode("ascii", errors="ignore")
            break

    if path_secret != expected_secret and header_secret != expected_secret:
        logger.warning("webhook secret mismatch path=%r", scope["path"])
        await _send_json(send, 403, {"error": "invalid_secret"})
        return

    body = await _read_body(receive)
    if not body:
        await _send_json(send, 400, {"error": "empty_body"})
        return

    try:
        update = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        logger.warning("webhook: invalid JSON body: %s", exc)
        await _send_json(send, 400, {"error": "invalid_json"})
        return

    try:
        await _route_update(update)
    except Exception:  # noqa: BLE001 — log + 200 OK so Telegram doesn't retry-storm
        logger.exception("webhook: handler crashed for update=%s", update.get("update_id"))

    # Telegram retries any non-2xx; always 200 once we've decoded the body so a
    # broken handler doesn't block the next update.
    await _send_json(send, 200, {"ok": True})


async def _route_update(update: dict[str, Any]) -> None:
    """Dispatch one Telegram Update to the right handler."""
    if "message" in update:
        await handle_message_update(update["message"])
        return
    if "callback_query" in update:
        await handle_callback_query(update["callback_query"])
        return
    logger.debug("webhook: ignoring update kind=%s", set(update.keys()))


async def app(scope, receive, send) -> None:
    """ASGI entrypoint.

    Routes `/bot/webhook/*` to our handler; falls back to Django for everything
    else so a single uvicorn invocation can serve both the bot webhook and the
    WebApp if Eric ever consolidates services.
    """
    if scope["type"] == "lifespan":
        # Drain lifespan messages so uvicorn doesn't hang waiting on us.
        await _drain_lifespan(scope, receive, send)
        return

    if scope["type"] == "http" and scope["path"].startswith(WEBHOOK_PATH_PREFIX):
        await handle_webhook(scope, receive, send)
        return

    # Everything else → Django (handles /healthz, /admin, and /app/* if rolled
    # into the same uvicorn process).
    await _django_app(scope, receive, send)


async def _drain_lifespan(_scope, receive, send) -> None:
    while True:
        message = await receive()
        if message["type"] == "lifespan.startup":
            await send({"type": "lifespan.startup.complete"})
        elif message["type"] == "lifespan.shutdown":
            await send({"type": "lifespan.shutdown.complete"})
            return


# Stop ruff complaining about the sync_to_async import — kept for handler use.
_ = sync_to_async
