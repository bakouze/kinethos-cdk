# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Kinethos is an AI-powered endurance coach (running, cycling, triathlon) that converts wearable/training data into simple, personalized, safe daily guidance. The goal is to democratize elite-level coaching — making it accessible without expensive coaches or fragmented tools.

**MVP channel:** Telegram bot. **Primary stack:** AWS CDK (Python), Amazon Bedrock, Aurora PostgreSQL Serverless v2 (target DB — currently DynamoDB).

### Product Principles

1. **Data-grounded recommendations** — always reference the user's real training history; explicitly say when data is missing.
2. **Clarity > complexity** — prioritize "what to do next" over exhaustive education.
3. **Progressive personalization** — start helpful with minimal inputs, improve with usage.
4. **Coaching, not healthcare** — hard boundary. Never diagnose, prescribe medication, or make clinical claims. Safety responses for pain/alarming symptoms.
5. **Grounding discipline** — only reference data you have; say when you don't. Hallucinated claims destroy trust.

### Current Phase: Pre-alpha

The codebase currently has basic Telegram bot infrastructure (webhook, onboarding, echo, `/ai_coach`). The target architecture involves adding: Garmin ingestion, Aurora PostgreSQL, coaching orchestrator with intent detection, and deterministic guardrails. See `Kinethos_Full_Documentation.md` for the full vision and roadmap.

## Common Commands

```bash
# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Synthesize CloudFormation template
cdk synth KinethosBotStack-dev -c stage=dev -c telegramToken="TOKEN" -c webhookSecret="SECRET"

# Deploy
cdk deploy KinethosBotStack-dev -c stage=dev -c telegramToken="TOKEN" -c webhookSecret="SECRET"

# Diff (preview changes)
cdk diff KinethosBotStack-dev -c stage=dev -c telegramToken="TOKEN" -c webhookSecret="SECRET"

# Destroy
cdk destroy KinethosBotStack-dev

# Run tests (currently empty)
pytest tests/
```

Docker must be running for `cdk synth` and `cdk deploy` (Lambda Python bundling uses Docker).

## Architecture

### Current State

```
Telegram → API Gateway (HTTP API, POST /bot) → Lambda (Python 3.11)
                                                  ├── Firehose → S3 (raw storage, GZIP, 365d expiry)
                                                  ├── DynamoDB (operational queries, 90d TTL)
                                                  └── AWS Bedrock (Claude 3.5 Sonnet)
```

### Target Architecture (from documentation)

```
Telegram → API Gateway → Lambda (Bot Router)
                            → Coaching Orchestrator (intent detection → context building → Bedrock → guardrails)
                            → Aurora PostgreSQL Serverless v2 (users, profiles, activities, chat_events)
                            → Amazon Bedrock (LLM)

Garmin/TrainingPeaks APIs → Ingestion Workers (EventBridge scheduled) → Normalizer → Aurora
```

**Key architectural patterns:**
- **Dual-write** (current): Every Telegram update written to both Firehose (cold/analytics) and DynamoDB (hot/operational). Non-blocking — failures logged but don't stop bot response.
- **Lambda warm-start optimization**: Bot Application instance is a singleton cached across warm invocations via `initialize()`.
- **Idempotent ingestion** (target): Unique constraint on `(provider, provider_activity_id)` in activities table.

## Code Structure

- `app.py` — CDK app entry point. Reads stage/token/secret from CDK context (`-c`) or environment variables.
- `kinethos_cdk/stacks/bot_stack.py` — Main stack. Wires constructs together and grants IAM permissions.
- `kinethos_cdk/constructs/` — Reusable CDK constructs:
  - `telegram_webhook.py` — Lambda + HTTP API Gateway
  - `updates_storage.py` — S3 bucket + Firehose delivery stream + IAM role + CloudWatch logs
  - `updates_table.py` — DynamoDB table (PK: `CHAT#`/`USER#`, SK: `TS#`/`PROFILE#v1`, GSI for update_id idempotency)
- `kinethos_cdk/services/telegram_bot/lambda_function.py` — Lambda handler (~400 lines). Contains:
  - Webhook secret validation
  - Onboarding conversation (9-state ConversationHandler with 10min timeout)
  - `/ai_coach` command calling Bedrock
  - Dual-write to Firehose and DynamoDB
- `kinethos_cdk/services/telegram_bot/requirements.txt` — Lambda-specific pip dependencies (bundled via Docker at deploy time)

### Target Module Structure (from documentation)

The documentation envisions evolving toward: `services/bot/` (routing), `services/coach/` (context builder + prompt engine + Bedrock), `services/ingestion/` (provider clients + sync jobs), `shared/` (types, migrations, utilities).

## Key Environment Variables (Lambda)

`TELEGRAM_TOKEN`, `WEBHOOK_SECRET_TOKEN`, `FIREHOSE_STREAM_NAME`, `DDB_TABLE_NAME`, `BEDROCK_MODEL_ID`, `BEDROCK_REGION`, `BEDROCK_MAX_TOKENS`, `BEDROCK_TEMPERATURE`, `BEDROCK_SYSTEM_PROMPT`

## Bot Intents (MVP)

The coaching orchestrator should handle these first-class intents:
1. **Daily recommendation** — "What should I do today?" → structured plan (session, why, how, watch-outs, short-time alternative)
2. **Weekly summary** — volume + intensity + consistency highlights + next week focus
3. **Adjustment** — "I missed a workout / slept poorly" → revised micro-plan for 3-7 days
4. **Ad-hoc Q&A** — grounded in user's data

### Deterministic Guardrails

- Hard session + fatigue in last 48h → avoid hard recommendation
- Weekly volume jump > threshold → caution
- Pain symptom keywords → safety response (stop, see professional)
- No recent activities → ask questions, propose gentle start

## Data Model (Target — Aurora PostgreSQL)

Key tables: `users` (telegram_user_id, status, timezone), `athlete_profile` (sports, goals, availability, constraints), `provider_connections` (encrypted tokens, sync status), `activities` (provider_activity_id unique, sport, duration, distance, HR, power, pace, training_load, raw_payload), `derived_metrics_daily` (volume, intensity distribution, fatigue flags), `chat_events` (messages, intent, latency, model_id).

## DynamoDB Schema (Current)

- **PK** (`pk`): `CHAT#{chat_id}` or `USER#{user_id}`
- **SK** (`sk`): `TS#{timestamp_ms}` or `PROFILE#v1`
- **TTL**: `expire_at` (90 days)
- **GSI1**: Lookup by `update_id` for idempotency
