# Kinethos — Telegram Webhook (AWS CDK, Python)

Minimal AWS infrastructure to run a Telegram bot via **webhook**:
- **API Gateway (HTTP API)** receives Telegram updates.
- **AWS Lambda (Python 3.11)** processes updates with `python-telegram-bot` v21.

> This repo is an MVP scaffold. It’s easy to extend with Bedrock calls, DynamoDB, etc.

---

## Architecture

```
Telegram → HTTPS Webhook (API Gateway HTTP API) → Lambda → CloudWatch Logs
```

- The Lambda handler caches a single `Application` instance and `initialize()` is called once per warm start.

---

## Prerequisites

- Python 3.11 (for CDK and Lambda runtime)
- Node.js + npm (for AWS CDK CLI)
- AWS CLI configured (`aws configure`)
- An existing Telegram **bot token** from @BotFather
- **Docker installed locally** (required by CDK to bundle Python dependencies)

---

## Docker Requirement

This project uses AWS CDK's bundling feature (e.g., `PythonFunction` or `BundlingOptions`) to package Python dependencies inside a Docker container automatically during deployment. 

Ensure Docker is installed and running on your local machine before deploying. You can verify by running:

```bash
docker --version
```

---

## Install

```bash
# in the project root
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Bootstrap the account/region once
export AWS_REGION=eu-central-1
cdk bootstrap aws://$AWS_ACCOUNT_ID/$AWS_REGION
```

---

## Deploy

Choose a stage name (e.g., `dev`) and provide secrets via **CDK context** or **env vars**.

During deployment, CDK will use Docker to bundle the Lambda function and its dependencies automatically.

```bash
# Option: pass secrets via -c context
cdk deploy KinethosBotStack-dev \
  -c stage=dev \
  -c telegramToken="YOUR_TELEGRAM_BOT_TOKEN" \
  -c webhookSecret="a-long-random-secret"
```

This creates:
- Lambda function (with dependencies bundled via Docker)
- API Gateway HTTP API

The stack outputs a `WebhookUrl` (e.g., `https://abc123.execute-api.eu-central-1.amazonaws.com/bot`).

---

## Set the Telegram Webhook

```bash
TOKEN="YOUR_TELEGRAM_BOT_TOKEN"
API_URL="https://abc123.execute-api.eu-central-1.amazonaws.com/bot"  # use the stack output
SECRET="a-long-random-secret"  # must match what you passed at deploy

curl -X POST "https://api.telegram.org/bot$TOKEN/setWebhook" \
  -d "url=$API_URL" \
  -d "secret_token=$SECRET"

# verify
curl -s "https://api.telegram.org/bot$TOKEN/getWebhookInfo" | jq
```

You should see `"url": "<API_URL>"` and no recent errors.

---

## Test

In Telegram, open your bot (@YourBotName) and try:

- `/ping` → `pong 🏓`
- `/start` → greeting
- Any text → echoed back

Tail logs while testing:

```bash
aws logs tail /aws/lambda/<YourFunctionName> --follow
```

---

## Troubleshooting

- **WebHook 500** in `getWebhookInfo`:
  - Check **CloudWatch Logs** for stack traces.
  - Ensure Lambda env vars: `TELEGRAM_TOKEN`, `WEBHOOK_SECRET_TOKEN` (if you set a secret).
  - Ensure handler path is `lambda_function.lambda_handler`.

- **No module named 'telegram'** or other dependency errors:
  - Make sure Docker is installed and running locally (`docker --version`).
  - CDK uses Docker to bundle dependencies during deployment.
  - Rerun `cdk deploy` to rebuild the Lambda package.

- **Secret mismatch**:
  - The header `X-Telegram-Bot-Api-Secret-Token` must equal `WEBHOOK_SECRET_TOKEN` in Lambda env.
  - Re-run `setWebhook` with the same secret you deploy.

---

## Teardown (avoid costs)

Disable the webhook and destroy stacks:

```bash
TOKEN="YOUR_TELEGRAM_BOT_TOKEN"
curl -X POST "https://api.telegram.org/bot$TOKEN/deleteWebhook"

cdk destroy KinethosBotStack-dev -c stage=dev
cdk destroy KinethosCdkStack-dev -c stage=dev
```

Optional cleanup:
- Delete any Secrets Manager/SSM secrets if you used them.

---

## Next Steps

- Add Bedrock calls in a separate Lambda (same stack or another stack).
- Store user state in DynamoDB (chat_id, last command, preferences).
- Add alarms (Lambda errors, 5XX on API Gateway) and log retention.