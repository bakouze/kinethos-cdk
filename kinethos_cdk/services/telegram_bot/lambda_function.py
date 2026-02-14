import json
import os
import base64
import asyncio
import logging
import time
from typing import Optional, Tuple
import boto3

from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    filters,
)

# --- Bedrock config via env vars ---
BEDROCK_MODEL_ID = os.getenv(
    "BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20240620-v1:0"
)
BEDROCK_REGION = os.getenv("BEDROCK_REGION", "eu-central-1")
BEDROCK_MAX_TOKENS = int(os.getenv("BEDROCK_MAX_TOKENS", "512"))
BEDROCK_TEMPERATURE = float(os.getenv("BEDROCK_TEMPERATURE", "0.2"))
BEDROCK_SYSTEM_PROMPT = os.getenv(
    "BEDROCK_SYSTEM_PROMPT", "You are a expert sport and nutrition coach."
)

brt = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

_app: Optional[Application] = None
_initialized: bool = False

_firehose = boto3.client("firehose")
_dynamodb = boto3.client("dynamodb")

FIREHOSE_STREAM = os.getenv("FIREHOSE_STREAM_NAME")
DDB_TABLE = os.getenv("DDB_TABLE_NAME")

# ---------- Onboarding conversation states ----------
(
    GOAL,
    EVENT,
    TIME_AVAIL,
    TRAINING_DAYS,
    CURR_TRAIN,
    EXPERIENCE,
    INJURIES,
    PREFS,
    DONE,
) = range(9)


def _save_user_profile(user_id: int, data: dict):
    """
    Persist the onboarding answers into DynamoDB as a compact user profile.
    Uses the same table but a different PK/SK than raw updates.
    """
    if not DDB_TABLE:
        logger.warning("DDB_TABLE not set; skipping profile save")
        return

    item = {
        "pk": {"S": f"USER#{user_id}"},
        "sk": {"S": "PROFILE#v1"},
        "updated_at": {"N": str(int(time.time()))},
        "profile": {"S": json.dumps(data, separators=(",", ":"))},
    }
    _dynamodb.put_item(TableName=DDB_TABLE, Item=item)


def _kb(options: list[list[str]]) -> ReplyKeyboardMarkup:
    """Build a compact one-time reply keyboard from rows of strings."""
    return ReplyKeyboardMarkup(options, resize_keyboard=True, one_time_keyboard=True)


# ---------- Bedrock handler ----------
def call_bedrock_anthropic(prompt: str) -> str:
    """
    Calls Anthropic Claude on Bedrock using the Messages API style request.
    Adjust if you choose a different provider (Cohere, Llama, etc.).
    """
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": BEDROCK_MAX_TOKENS,
        "temperature": BEDROCK_TEMPERATURE,
        "system": BEDROCK_SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}],
    }

    resp = brt.invoke_model(
        modelId=BEDROCK_MODEL_ID,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(body),
    )
    payload = json.loads(resp["body"].read())

    # Extract text from Anthropic response
    # payload format: {'id':..., 'content':[{'type':'text','text':'...'}], ...}
    parts = payload.get("content", [])
    texts = [
        p.get("text", "")
        for p in parts
        if isinstance(p, dict) and p.get("type") == "text"
    ]
    return "\n".join(t for t in texts if t)


# ---------- PTB handlers ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # initialize onboarding dict
    context.user_data["onb"] = {}
    await update.message.reply_text(
        "👋 Welcome to Kinethos! I’ll ask a few quick questions to tailor your plan. "
        "First up: what’s your main goal right now?\n"
        "e.g., marathon, improve cycling endurance, get fitter, balance training with life."
    )
    return GOAL


async def ask_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["onb"]["goal"] = (update.message.text or "").strip()
    kb = _kb([["Yes", "No"]])
    await update.message.reply_text(
        "Do you have a specific event or race in mind? If yes, please share the date and distance. "
        "If not, just tap No.",
        reply_markup=kb,
    )
    return EVENT


async def ask_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["onb"]["event"] = (update.message.text or "").strip()
    await update.message.reply_text(
        "How many hours do you realistically have for training each week? ",
        reply_markup=ReplyKeyboardRemove(),
    )
    return TIME_AVAIL


async def ask_training_days(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["onb"]["time_available"] = (update.message.text or "").strip()
    await update.message.reply_text("On which days do you want to train each week? ")
    return TRAINING_DAYS


async def ask_curr_train(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["onb"]["training_days"] = (update.message.text or "").strip()
    await update.message.reply_text(
        "What does your current training look like?\n"
        "For example: how often you run, cycle, do strength, or if you’re starting fresh.",
        reply_markup=ReplyKeyboardRemove(),
    )
    return CURR_TRAIN


async def ask_experience(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["onb"]["current_training"] = (update.message.text or "").strip()
    kb = _kb([["Beginner", "Intermediate", "Advanced"]])
    await update.message.reply_text(
        "How experienced do you feel in endurance sports?",
        reply_markup=kb,
    )
    return EXPERIENCE


async def ask_injuries(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["onb"]["experience"] = (update.message.text or "").strip()
    await update.message.reply_text(
        "Do you have any injuries or physical limitations I should take into account?",
        reply_markup=ReplyKeyboardRemove(),
    )
    return INJURIES


async def ask_prefs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["onb"]["injuries"] = (update.message.text or "").strip()
    kb = _kb([["Running", "Cycling"], ["Strength", "Mix"]])
    await update.message.reply_text(
        "What type of training do you enjoy most?",
        reply_markup=kb,
    )
    return PREFS


async def finish_onboarding(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["onb"]["preferences"] = (update.message.text or "").strip()
    # Persist to DynamoDB
    user_id = update.effective_user.id if update.effective_user else None
    if user_id is not None:
        _save_user_profile(user_id, context.user_data["onb"])
    await update.message.reply_text(
        "Awesome — thank you! 🎉 I’ve saved your answers and will craft your first training plan next.",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "No worries — we can set this up anytime. Just send /start to begin again."
    )
    return ConversationHandler.END


async def ai_coach(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat

    # 1) prefer argument after /ai_coach
    args_text = " ".join(context.args).strip() if context.args else ""

    # 2) or, if the user replied to a message, use that text
    if not args_text and update.message and update.message.reply_to_message:
        args_text = (update.message.reply_to_message.text or "").strip()

    if not args_text:
        await chat.send_message(
            "Usage:\n"
            "/ai_coach <your text>\n\n"
            "Tip: you can also reply to any message with /ai_coach and I’ll use that text."
        )
        return

    # 3) acknowledge quickly
    await chat.send_message("🤖 Running your prompt through Bedrock…")

    try:
        answer = call_bedrock_anthropic(args_text)
        if not answer:
            answer = "_(Model returned no text)_"
        await _send_chunked(chat, answer)
    except Exception:
        logging.exception("Bedrock call failed")
        await chat.send_message(
            "Sorry, I couldn’t reach Bedrock or parse the response. Check logs."
        )


# ---------- PTB app lifecycle ----------
def _build_app() -> Application:
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        raise RuntimeError("Missing TELEGRAM_TOKEN env variable")

    application = Application.builder().token(token).build()

    # Onboarding conversation
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            GOAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_event)],
            EVENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_time)],
            TIME_AVAIL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, ask_training_days)
            ],
            TRAINING_DAYS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, ask_curr_train)
            ],
            CURR_TRAIN: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, ask_experience)
            ],
            EXPERIENCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_injuries)],
            INJURIES: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_prefs)],
            PREFS: [MessageHandler(filters.TEXT & ~filters.COMMAND, finish_onboarding)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        conversation_timeout=600,  # 10 minutes of inactivity
    )
    application.add_handler(conv)

    application.add_handler(CommandHandler("ai_coach", ai_coach))
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


# ---------- Helpers ----------
def _extract_ids(update_json: dict) -> Tuple[Optional[int], int]:
    """Return (chat_id, epoch_ms) for the update."""
    now_ms = int(time.time() * 1000)
    chat_id = None
    # Common cases
    msg = update_json.get("message") or update_json.get("edited_message")
    if msg and "chat" in msg and "id" in msg["chat"]:
        chat_id = msg["chat"]["id"]
        # Telegram 'date' field is seconds; convert to ms if present
        if "date" in msg:
            try:
                now_ms = int(msg["date"]) * 1000
            except Exception:
                pass
    # Fallbacks (callback_query, etc.)
    if chat_id is None:
        cq = update_json.get("callback_query")
        if cq and "message" in cq and "chat" in cq["message"]:
            chat_id = cq["message"]["chat"].get("id")
    return chat_id, now_ms


def _put_firehose(update_json: dict):
    """Put the update into Firehose."""
    logger.info("Putting update into Firehose")
    if not FIREHOSE_STREAM:
        return
    data = (json.dumps(update_json, separators=(",", ":")) + "\n").encode("utf-8")
    _firehose.put_record(DeliveryStreamName=FIREHOSE_STREAM, Record={"Data": data})


def _put_dynamo(update_json: dict):
    """Put the update into DynamoDB."""
    logger.info("Putting update into DynamoDB")
    if not DDB_TABLE:
        return
    chat_id, ts_ms = _extract_ids(update_json)
    pk = f"CHAT#{chat_id}" if chat_id is not None else "CHAT#unknown"
    sk = f"TS#{ts_ms}"
    update_id = update_json.get("update_id")
    # TTL in 90 days
    expire_at = int(time.time()) + 90 * 24 * 3600

    item = {
        "pk": {"S": pk},
        "sk": {"S": sk},
        "update_id": {"N": str(update_id)}
        if isinstance(update_id, int)
        else {"S": str(update_id)},
        "payload": {"S": json.dumps(update_json, separators=(",", ":"))},
        "expire_at": {"N": str(expire_at)},
    }
    # Optional GSI for idempotency lookup
    item["gsi1pk"] = {"S": f"UPDATE#{update_id}"}
    item["gsi1sk"] = {"S": pk}

    _dynamodb.put_item(TableName=DDB_TABLE, Item=item)


async def _send_chunked(chat, text: str):
    max_len = 4096
    for i in range(0, len(text), max_len):
        await chat.send_message(text[i : i + max_len])


# ---------- Lambda entry ----------
def lambda_handler(event, context):
    # 1) Verify secret header if configured
    expected = os.getenv("WEBHOOK_SECRET_TOKEN")
    if expected:
        headers = event.get("headers") or {}
        supplied = headers.get("X-Telegram-Bot-Api-Secret-Token") or headers.get(
            "x-telegram-bot-api-secret-token"
        )
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
        logger.exception("Failed to parse request body as JSON: %s", e)
        return {"statusCode": 400, "body": "invalid body"}

    # 3) Dual-write BEFORE bot logic (so we capture even if bot handler fails)
    try:
        _put_firehose(update_json)
    except Exception:
        logger.exception("Firehose put_record failed")
    try:
        _put_dynamo(update_json)
    except Exception:
        logger.exception("DynamoDB put_item failed")

    # 4) Process the update with PTB
    try:
        loop = asyncio.get_event_loop()
        app = loop.run_until_complete(_ensure_initialized())
        update = Update.de_json(update_json, app.bot)
        loop.run_until_complete(app.process_update(update))
        logger.info(body)
    except Exception:
        logger.exception("Error while processing Telegram update")
        # Return 200 so Telegram doesn't keep retrying *forever* while you debug,
        # but keep the error in logs. Change to 500 once stable if you prefer retries.
        return {"statusCode": 200, "body": "error logged"}

    # 4) All good
    return {"statusCode": 200, "body": "OK"}
