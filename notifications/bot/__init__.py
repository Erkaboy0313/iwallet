"""Telegram bot package (Epic 9).

`bot.webhook` exposes the ASGI entrypoint uvicorn loads in production
(`iwallet-bot.service`). `bot.telegram_client` is the thin async wrapper
around the Bot API. Handlers live alongside in `bot.handlers`.
"""
