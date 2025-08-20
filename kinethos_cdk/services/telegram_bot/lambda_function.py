import json
import os
import base64
import asyncio
import logging
from typing import Optional

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

_app: Optional[Application] = None
_initialized: bool = False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 KinethosBot (Lambda webhook). Try /ping or say hi.")


async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("pong 🏓")


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Echo: {update.message.text or ''}")


def _build_app() -> Application:
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        raise RuntimeError("Missing TELEGRAM_TOKEN env variable")

    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("ping", ping))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    return application


async def _ensure_initialized() -> Application:
    """Build (once) and initialize PTB Application (once per warm Lambda)."""
    global _app, _initialized
    if _app is None:
        _app = _build_app()
    if not _initialized:
        await _app.initialize()
        # We don't call .start()/.stop() in this pattern; initialize is enough for processing updates.
        _initialized = True
        logger.info("PTB Application initialized")
    return _app


def lambda_handler(event, context):
    # 1) Verify secret header if configured
    expected = os.getenv("WEBHOOK_SECRET_TOKEN")
    if expected:
        headers = event.get("headers") or {}
        supplied = headers.get("X-Telegram-Bot-Api-Secret-Token") or headers.get("x-telegram-bot-api-secret-token")
        if supplied != expected:
            logger.warning("Secret token mismatch")
            return {"statusCode": 401, "body": "unauthorized"}

    # 2) Decode body safely
    body = event.get("body", "")
    if event.get("isBase64Encoded"):
        body = base64.b64decode(body)
    if isinstance(body, (bytes, bytearray)):
        body = body.decode("utf-8")

    try:
        update_json = json.loads(body)
    except Exception as e:
        logger.exception("Failed to parse request body as JSON")
        return {"statusCode": 400, "body": "invalid body"}

    # 3) Process the update with PTB
    try:
        loop = asyncio.get_event_loop()
        app = loop.run_until_complete(_ensure_initialized())
        update = Update.de_json(update_json, app.bot)
        loop.run_until_complete(app.process_update(update))
    except Exception:
        logger.exception("Error while processing Telegram update")
        # Return 200 so Telegram doesn't keep retrying *forever* while you debug,
        # but keep the error in logs. Change to 500 once stable if you prefer retries.
        return {"statusCode": 200, "body": "error logged"}

    # 4) All good
    return {"statusCode": 200, "body": "OK"}