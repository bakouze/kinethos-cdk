#!/usr/bin/env python3
import os
import aws_cdk as cdk

# BotStack will host the Telegram webhook (HTTP API + Lambda)
# Make sure you have kinethos_cdk/stacks/bot_stack.py implemented as discussed.
from kinethos_cdk.stacks.bot_stack import BotStack

app = cdk.App()

# ----- Environment & Stage -----
stage = app.node.try_get_context("stage") or os.getenv("STAGE", "dev")

# Prefer CLI-provided account/region; fall back to explicit defaults
account = os.getenv("CDK_DEFAULT_ACCOUNT") or "884551077777"
region = os.getenv("CDK_DEFAULT_REGION") or "eu-central-1"

env = cdk.Environment(account=account, region=region)

# ----- Telegram Bot (webhook) stack -----
# Secrets can be provided via CDK context (-c) or environment variables
telegram_token = (
    app.node.try_get_context("telegramToken")
    or os.getenv("TELEGRAM_TOKEN")
    or ""
)

webhook_secret = (
    app.node.try_get_context("webhookSecret")
    or os.getenv("WEBHOOK_SECRET_TOKEN")
    or ""
)

bot_stack = BotStack(
    app,
    f"KinethosBotStack-{stage}",
    env=env,
    telegram_token=telegram_token,
    webhook_secret=webhook_secret,
    lambda_code_path="kinethos_cdk/services/telegram_bot",  # folder containing lambda_function.py
    webhook_path="/bot",
)

app.synth()
