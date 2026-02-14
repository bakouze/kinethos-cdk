# Kinethos — Full Project Documentation

**Owner:** Guillaume Boulanger  
**Primary goal:** Build an AI-powered endurance coach that converts wearable/training data into *simple, personalized, safe* daily guidance and accountability.  
**MVP channel:** Telegram bot  
**Primary stack:** AWS (CDK), Amazon Bedrock, Aurora PostgreSQL Serverless v2  
**Last updated:** 2026-02-13 (Europe/Luxembourg)

---

## Table of contents

1. [Executive summary](#executive-summary)  
2. [Problem and motivation](#problem-and-motivation)  
3. [Vision](#vision)  
4. [Product scope](#product-scope)  
5. [MVP: definition and requirements](#mvp-definition-and-requirements)  
6. [User experience (Telegram flows)](#user-experience-telegram-flows)  
7. [Success metrics](#success-metrics)  
8. [System architecture](#system-architecture)  
9. [Technical design (MVP)](#technical-design-mvp)  
10. [Data model](#data-model)  
11. [Integrations](#integrations)  
12. [Coaching intelligence (LLM + rules)](#coaching-intelligence-llm--rules)  
13. [Security, privacy, and compliance](#security-privacy-and-compliance)  
14. [Observability, ops, and runbooks](#observability-ops-and-runbooks)  
15. [Testing strategy](#testing-strategy)  
16. [Costs and scaling](#costs-and-scaling)  
17. [Current progress](#current-progress)  
18. [Roadmap](#roadmap)  
19. [Risks and open questions](#risks-and-open-questions)  
20. [Appendices](#appendices)  

---

## Executive summary

Kinethos is an AI training coach for endurance sports (running, cycling, triathlon). It exists to close the gap between:

- **the data people already have** (Garmin / wearables / training logs),
- **the training science that works** (progressive overload, recovery, habit formation),
- **and the daily decisions athletes struggle with** (“What should I do today?”, “Am I overdoing it?”, “How do I adjust after a bad night or missed session?”).

The MVP is intentionally minimal: a **Telegram bot** that connects to a user’s training provider, ingests recent activity data, and provides **daily recommendations, weekly summaries, and adaptive adjustments** grounded in their history—powered by **Amazon Bedrock** and a small set of deterministic guardrails.

---

## Problem and motivation

Below is the project’s core problem statement (as authored in your working doc), condensed into the essential themes:

- People are **stuck at the starting line** (beginners) or **plateau below their potential** (enthusiasts), not because they lack discipline, but because support is fragmented, impersonal, and hard to apply consistently.
- Beginners face contradictory advice, no easy entry point, and often fall into “too much too soon”.
- Enthusiasts have tons of data, but limited interpretation, weak feedback loops, and “static” plans that don’t adapt to life.

### Canonical source (verbatim working doc)

Over the past five years, both in my own athletic journey and through helping friends start running or cycling, I’ve seen the same problem repeatedly: **people are either stuck at the starting line or plateau far below their potential**, not because they lack discipline, but because the tools, advice, and support they need are fragmented, impersonal, and often counterproductive.
### **1. For Beginners: Getting Started Feels Overwhelming or Risky**

- **Motivation barrier**: Many aspiring runners or cyclists never take the first step. Advice online is contradictory, intimidating, and disconnected from their personal situation.
- **No easy entry point**: Establishing a routine feels impossible without structure or feedback.
- **The “Strava trap”**: Motivated beginners often do too much too soon, chasing metrics and public validation. They feel embarrassed to post short, slow workouts, push beyond safe limits, get injured, and quit for months.
- **One-size-fits-all advice**: Current beginner training plans treat all novices the same, ignoring starting fitness, health conditions, or past athletic experience. An already-fit cyclist and an overweight sedentary beginner get the same generic plan, which is ineffective for both.
### **2. For Intermediate & Advanced Amateurs: Training Is Fragmented and Untailored**

- **Scattered tools**: Athletes juggle multiple platforms for plans (TrainingPeaks, Garmin Coach), tracking (Garmin, Strava, Whoop), and nutrition, none of which talk to each other.
- **Generic or expensive plans**: Paid plans are static, rarely adapted to real-life performance. Coaches can personalize but are expensive, slow to respond, and limited by human bandwidth.
- **No true multi-sport integration**: Marathon plans don’t account for cycling and strength training sessions; triathlon training doesn’t dynamically adapt to changes in any single discipline.
- **No holistic adaptation**: Current tools don’t combine training data with recovery, sleep, nutrition, and goals to provide integrated, real-time adjustments.
- **Multiple goals conflict**: Athletes with diverse objectives (e.g., sub-3 marathon, summer bike races, muscle building) are left to manually reconcile conflicting advice and plans.
- **Nutrition & supplementation ignored**: Most training plans are blind to dietary habits, micronutrient deficiencies, or supplements that could improve performance.
### **3. The Core Gap: A True AI-Powered, Holistic Coach for All Athletes**

Today, only **professional athletes with full-time coaches, nutritionists, and health staff** can truly optimize every aspect of training and health. For everyone else, data already captured by smartwatches and health trackers sits underused in silos.

In an era where **AI can process and personalize vast amounts of data instantly**, it is absurd that most athletes, beginner or advanced, still rely on static, generic advice. There’s a massive opportunity for an **AI-driven, fully integrated coaching solution** that:

- **Meets beginners where they are**, removing friction, building habits safely, and keeping motivation high.
- **Optimizes advanced athletes’ training**, integrating all available data (training load, recovery, nutrition, sleep) to adapt plans in real time.
- **Democratizes elite-level coaching**, making it accessible at a fraction of the cost.

---

## Vision

### North star
**Make high-quality, personalized endurance coaching accessible to anyone—without the overhead of spreadsheets, expensive coaching, or hours of research.**

### What Kinethos feels like
- A coach in your pocket: lightweight, always available, low-friction.
- *Actionable over verbose*: “Do this today, here’s why, here’s how.”
- Safe and pragmatic: nudges consistency, protects recovery, avoids injury traps.
- Learns over time: preferences, constraints, response patterns, and goals.

### Product principles
1. **Data-grounded recommendations** — always reference the user’s real training history (or explicitly say when data is missing).
2. **Clarity > complexity** — prioritize “what to do next” over exhaustive education.
3. **Progressive personalization** — start helpful with minimal inputs, improve with usage and feedback.
4. **Behavior is first-class** — adherence, motivation, and confidence are outcomes, not side effects.
5. **Privacy by design** — minimize data collection, transparency on storage/usage, deletion built-in.

---

## Product scope

### Target users
1. **Beginners / returners**: want structure, safety, confidence, and consistency.
2. **Enthusiasts / self-coached**: want adaptive programming and interpretation of signals.
3. **Time-constrained**: want best ROI from limited hours.

### Key use cases
- Daily recommendation: “What should I do today?”
- Weekly summary: “How did I do this week and what should I focus on next?”
- Adjustment: “I missed a workout / traveled / slept poorly — adjust my week.”
- Understanding: “Why am I plateauing?” “What does my intensity distribution mean?”

### Explicit non-goals (MVP)
- Not a medical or rehab tool.
- Not an elite-level periodization engine (yet).
- No complex multi-sport calendar UI: Telegram-first.

---

## MVP definition and requirements

### MVP goal
Validate that a chat-first AI coach can reliably:
1) ingest training data,  
2) produce useful daily/weekly guidance,  
3) increase adherence and user confidence/trust.

### MVP scope (in)
- Telegram bot interface
- Provider connection (Garmin first)
- Incremental ingestion + storage in Aurora PostgreSQL
- LLM coaching grounded in user profile + recent training history
- First-class intents:
  - daily recommendation
  - weekly summary
  - adjustment (missed session / fatigue / travel)
  - ad-hoc Q&A grounded in data
- Basic admin/debug tooling for early cohort support

### MVP scope (out)
- Multi-platform apps (mobile/web app beyond minimal landing)
- Social features
- Full subscription/paywall (optional for later)
- Full “plan builder” months ahead (beyond micro-plans + adjustments)

### Functional requirements (MVP)
- FR1: `/start` onboarding and capture minimum athlete profile inputs.
- FR2: Connect Garmin account and store tokens securely.
- FR3: Ingest activities (and optionally key recovery signals if available).
- FR4: Respond to core intents with grounded, structured answers.
- FR5: Maintain user state + auditability (what data was used for a response).
- FR6: Account deletion (remove personal data + revoke provider connection where possible).

### Non-functional requirements (MVP)
- NFR1: Ingestion is idempotent and retry-safe.
- NFR2: Median bot response time feels “chatty” (target: <10s typical).
- NFR3: Security: least privilege, encryption at rest/in transit.
- NFR4: Cost discipline: serverless + caching + tiered model usage.
- NFR5: Observability: ingestion health + error monitoring from day 1.

---

## User experience (Telegram flows)

### 1) Onboarding flow
- `/start`
- Explain: what Kinethos does + disclaimers (not medical)
- Capture:
  - sports (run/ride/swim)
  - goal (race type/date or general objective)
  - availability (days/week or hours/week)
  - experience level
  - constraints (injury history, preferences, schedule constraints)
- “Connect Garmin” call-to-action (OAuth flow link)
- Confirmation + first “baseline summary” message

### 2) Daily recommendation
User: “What should I do today?”  
Kinethos:
- retrieves last 7–21 days of training and simple fatigue heuristics
- returns a structured plan:
  - **Today’s session**
  - **Why**
  - **How**
  - **Watch-outs**
  - **Alternative if short on time**

### 3) Weekly summary
User: “Weekly summary”  
Kinethos:
- summarizes volume + intensity distribution + consistency
- highlights 1–2 strengths and 1 improvement
- suggests next week focus and one key workout

### 4) Adjustment / exception handling
User: “I missed yesterday, slept badly, can you adjust?”  
Kinethos:
- proposes a revised micro-plan for the next 3–7 days
- explains tradeoffs (recovery vs stimulus, goal proximity, etc.)

### 5) Safety boundaries
If user indicates severe pain, alarming symptoms, or asks for diagnosis:
- Provide a safety response:
  - encourage stopping the session,
  - recommend professional medical evaluation,
  - avoid definitive medical claims.

---

## Success metrics

### Product-market signals (alpha/beta)
- **Activation:** % who connect Garmin and receive first useful recommendation (within 24h).
- **Retention:** D7 / D30 retention (returning and using bot).
- **Adherence proxy:** % of days with “recommendation → activity within 24–48h” (best-effort).
- **User trust:** quick in-chat rating (“Was this helpful?” thumbs up/down + reason).
- **Quality:** hallucination rate (claims not supported by data), safety incident rate.

### MVP “definition of success”
- Small cohort (10–30) where:
  - ≥50% D30 retention **or** clear qualitative pull (“I miss it when I don’t use it”),
  - high trust (low hallucination complaints),
  - users report reduced decision fatigue + better consistency.

---

## System architecture

```text
Telegram User
   |
   v
Telegram Webhook -> API Gateway -> Lambda (Bot Router)
                                   |
                                   v
                         Coaching Orchestrator (Lambda)
                          - load athlete profile & context
                          - retrieve recent activities/aggregates
                          - call Bedrock
                          - apply safety + formatting
                                   |
                 +-----------------+-----------------+
                 |                                   |
                 v                                   v
      Aurora PostgreSQL (Serverless v2)         Amazon Bedrock (LLM)
      - users, tokens, activities, logs         - generation/runtime
      - aggregates, recommendations
                 ^
                 |
Garmin / TrainingPeaks APIs
   |
   v
Ingestion Workers (scheduled) -> Queue (optional) -> Normalizer -> DB
```

---

## Technical design (MVP)

### Repository / modules (suggested)
- `infra/` — AWS CDK stacks
- `services/bot/` — Telegram webhook + routing
- `services/coach/` — context builder + prompt engine + Bedrock client
- `services/ingestion/` — provider clients + sync jobs + normalization
- `shared/` — types, schema migrations, utilities
- `docs/` — PRFAQ, privacy policy, architecture notes

### AWS components (MVP-friendly)
- **API Gateway** (or ALB) for Telegram webhook endpoint
- **Lambda** for:
  - webhook handler
  - coaching orchestrator
  - ingestion workers
- **Aurora PostgreSQL Serverless v2** for persistence
- **Secrets Manager / KMS** for provider tokens and app secrets
- **EventBridge Scheduler** for ingestion cadence
- **CloudWatch** logs + alarms

### Environments
- `dev` — sandbox
- `uat` — early user testing (separate DB/secrets)
- `prod` — real users

### Ingestion pipeline details
- **Trigger:** EventBridge schedule per environment (e.g., hourly) + per-user incremental cursors.
- **Idempotency:** unique constraint on `(provider, provider_activity_id)` in `activities`.
- **Backfill:** when a connection is first created, sync last N days (e.g., 90) with paging.
- **Failure handling:** retries with exponential backoff; persistent errors flagged on `provider_connections`.

### Coaching orchestrator details
- **Intent detection:** lightweight classifier (rules or LLM) to map messages to intents:
  - daily recommendation
  - weekly summary
  - adjustment
  - general Q&A
- **Context window:** pull a compact summary + a small selection of “anchor activities” (last long, last hard, last easy, most recent).
- **Prompt construction:** system rules + user goal + summary + extracted activity facts.
- **Post-processing:**
  - enforce structure and brevity
  - sanity checks (no impossible intensity jumps)
  - safety responses when needed

---

## Data model

Below is a practical MVP schema. Keep it stable and versioned with migrations.

### `users`
- `user_id` UUID PK
- `telegram_user_id` unique
- `created_at`, `updated_at`
- `timezone`, `language`
- `status` (active/paused/deleted)

### `athlete_profile`
- `user_id` PK/FK
- `experience_level`
- `sports` (json/array)
- `availability_hours_per_week` (nullable)
- `goals` (json: race type/date/target)
- `constraints` (json: injuries, schedule, preferences)

### `provider_connections`
- `connection_id` PK
- `user_id` FK
- `provider` (garmin/trainingpeaks/…)
- `access_token` (encrypted)
- `refresh_token` (encrypted, nullable)
- `scopes` (json/text)
- `connected_at`
- `last_synced_at`
- `status` (ok/expired/error)
- `error_reason` (nullable)

### `activities`
- `activity_id` UUID PK
- `user_id` FK
- `provider`
- `provider_activity_id` (unique with provider)
- `sport` (run/ride/swim/strength/other)
- `start_time_utc`
- `duration_sec`
- `distance_m` (nullable)
- `elevation_gain_m` (nullable)
- `avg_hr`, `max_hr` (nullable)
- `avg_power_w`, `max_power_w` (nullable)
- `avg_pace_sec_per_km` (nullable)
- `training_load` (nullable)
- `raw_payload` jsonb (optional but helpful for debugging/backfill)

Indexes:
- `(user_id, start_time_utc desc)`
- `(provider, provider_activity_id)`

### `derived_metrics_daily` (recommended)
- `user_id`
- `date`
- `volume_by_sport` (json)
- `intensity_distribution` (json)
- `acute_load`, `chronic_load` (optional)
- `fatigue_flags` (json)

### `chat_events`
- `event_id`
- `user_id`
- `timestamp_utc`
- `source` (telegram)
- `user_message`
- `assistant_message`
- `intent` (optional)
- `latency_ms`
- `model_id` (optional)
- `cost_estimate` (optional)

### `coach_recommendations` (optional)
- `rec_id`
- `user_id`
- `created_at`
- `type` (daily/weekly/adjustment)
- `content` (json/text)
- `references` (json of activity_ids used)

---

## Integrations

### Garmin (first priority)
Purpose: ingest activities and key signals for grounded coaching.

- Activities: duration, distance, HR, power, pace, sport type
- Optional recovery signals if permissioned: sleep/HRV/body battery

Operational considerations:
- token refresh stability
- rate limits
- paging/backfill strategy
- handling duplicates and corrections

**Status:** Garmin API access secured.

### TrainingPeaks (next)
Purpose: planned workouts + structured training plans.

- planned vs completed workouts
- matching logic between plan and execution
- richer metadata (workout structure)

**Status:** planned/in progress.

---

## Coaching intelligence (LLM + rules)

### Design philosophy (MVP)
LLM is the *communication + reasoning* engine, but guardrails ensure:
- advice remains safe,
- references remain grounded,
- tone is consistent,
- output is actionable.

### Prompting (recommended structure)
- System: coaching principles, safety disclaimers, style guide, grounding rules
- Developer: intent-specific templates
- User: message
- Context: athlete profile + compact training summary + selected activity facts

### Deterministic guardrails (high value early)
- If last 48h include hard session + fatigue flag → avoid hard recommendation
- If weekly volume jumps > X% → caution
- If user reports pain symptoms keywords → safety response
- If missing data (no recent activities) → ask minimal questions + propose gentle start

### Response format (Telegram-friendly)
- **Recommendation:** …
- **Why:** …
- **How:** …
- **If you feel worse than expected:** …
- **Alternative (short time):** …

---

## Security, privacy, and compliance

### Security baseline
- Encrypt tokens (KMS) and store in Secrets Manager or encrypted DB fields
- TLS for all endpoints
- Least-privilege IAM per Lambda
- Environment separation (dev/uat/prod) with distinct secrets and DBs
- Avoid storing unnecessary PII

### Privacy posture
- Clear privacy policy: what is collected, why, retention, deletion
- Account deletion:
  - remove user profile + activities + chat logs (as designed)
  - revoke provider token where possible
- Transparency in onboarding: “Your data is used to generate training guidance.”

### Compliance boundary
- Kinethos is **not medical advice**.
- Avoid diagnosing, prescribing medication, or making clinical claims.

---

## Observability, ops, and runbooks

### What to monitor
- Webhook error rate
- Bedrock latency and errors
- Ingestion success rate + last sync age per user
- DB saturation/connection errors
- Cost alarms (Bedrock usage spikes)

### Recommended alarms
- Ingestion failures above threshold
- No successful sync for >24h (active users)
- Webhook 5xx spike
- Budget alert for LLM spend

### Runbooks (MVP level)
- **Provider auth expired:** mark connection as expired; prompt user to reconnect.
- **Ingestion stuck:** re-run sync for user; inspect last cursor and raw payload.
- **Hallucination report:** inspect `chat_events` + `references` used; update prompt/filters.

---

## Testing strategy

### Unit tests
- Provider client parsing (sample payloads → normalized `activities`)
- Context builder (given activities → correct summary)
- Guardrails (fatigue/pain keywords → correct safety response)

### Integration tests
- End-to-end: Telegram update → response (mock Bedrock)
- DB migrations apply cleanly in CI

### Prompt regression tests (high leverage)
- Maintain a small set of canonical scenarios:
  - beginner first week
  - too much intensity
  - missed sessions
  - travel week
- Snapshot expected output format and “no hallucination” constraints.

---

## Costs and scaling

### Main cost drivers
- Bedrock requests per user/day
- Aurora capacity
- Ingestion polling frequency
- Logs retention

### Cost controls
- Cache daily/weekly summaries
- Use smaller model for summarization/classification, larger for final message (if needed)
- Reduce ingestion frequency for inactive users
- Nightly batch job for derived metrics if real-time is not needed

---

## Current progress

This section captures what is known so far from project context and your artifacts:

- **Vision and PRFAQ work**: outline drafted (press release + FAQ structure).
- **Problem statement**: written and refined (beginner + enthusiast gap; fragmentation; “wearables already have the data”).
- **MVP approach**: Telegram-only to iterate quickly.
- **AWS foundation**: building on AWS with CDK, Bedrock integration, Aurora PostgreSQL Serverless v2.
- **Integrations**: Garmin API access secured; TrainingPeaks planned/in progress.
- **Early ops/brand assets**: UAT approach and privacy/brand considerations started.

---

## Roadmap

### Phase 0 — Pre-alpha (now)
- Finalize canonical schema + migrations
- Make ingestion reliable (idempotent, retry-safe, backfill)
- Implement first-class intents (daily/weekly/adjustment)
- Add account deletion + privacy policy
- Add monitoring + cost alarms

### Phase 1 — Alpha (10–30 users)
- Instrument feedback loops (thumbs up/down + reasons)
- Reduce hallucinations and increase grounding fidelity
- Improve personalization: time constraints, preferred sports split, injury constraints
- TrainingPeaks integration if “planned workouts” is a key differentiator

### Phase 2 — Beta
- Minimal web landing/settings page
- Better “plan adjustment” micro-planning for 3–14 days
- Optional subscriptions/payments

### Phase 3 — Expansion
- Multi-channel interfaces
- Social/accountability modes
- Advanced analytics and performance modeling (only if validated)

---

## Risks and open questions

### Product risks
- **Trust is everything:** one hallucinated claim can kill adoption.
- **Too verbose:** long responses reduce daily usage.
- **Generic advice:** if personalization is weak, it becomes “chatGPT with running tips”.

### Technical risks
- Provider API changes, token refresh issues, rate limiting
- Bedrock latency and cost variability
- Data normalization inconsistencies across providers

### Key open questions to decide early
- What “training philosophy” is Kinethos opinionated about (polarized vs pyramidal, etc.)?
- Minimum data set for good advice without brittleness?
- How to measure coaching quality beyond retention (adherence, injuries, performance trends, confidence)?

---

## Appendices

### Appendix A — PRFAQ outline (working document)

## 1. Press Release - Luxembourg, January 2026

- **Headline**: Announce the launch of the AI Coach and highlight its unique benefit.
- **Subheading**: One sentence that explains what it is and why it matters.
- **Body**:
    - Problem the product solves:
	    - Very hard to start health journey (beginners), or to train optimally without headache (enthusiasts), only professionals get tailored support: Coach, physiotherapist, Nutritionist, ...
	    - + Summary of the problem statement
	    - We already collect the right data: almost everyone wears a smartwatch (Garmin, Whoop, Oura ring, ...)
	    - Habit formation and training science exists but is in no way accessible
    - How Kinethos works:
	    - Kinethos, the first AI training coach
	    - reads all your health and fitness data from Strava, Garmin, Whoop, ...
	    - Proactively reaches out to you, like a real coach: Whatsapp messages and calls
	    - Your coach will ask you about your goals and motivation, design a plan tailored to your needs and adapt it to fit your lifestyle
	    - Kinethos can answer all your questions, provide guidance and dynamically adapt your targets
    - Key benefits for the target audience.
	    - Kinethos truly knows and cares about you and your priorities: no more awaiting for your expensive coach to answer your email, or tinkering manually with your plan
	    - Kinethos will reach out to you in the morning to explain your main recovery metrics: sleep quality, Resting Heart Rate, Heart Rate Variability, ... and explain how those reflect your past training and impact your target for the day! Low HRV after a tough interval session: better to take it slightly easier today, go for a 20 min Z2 run and then stretch for 30 min!
	    - can answer all your questions based on scientific research: "Today's run felt too difficult, I struggled to keep the expected pace and my heart rate was too high. Is that normal? What should I do to meet my marathon goal?"
    - Customer quotes (imagined but realistic).
    - Closing with availability & call to action.

## **2. FAQ – External (Customer Perspective)**

- **What is Kinethos?**
	- take key points from above
- **Who is it for?**
	- Everyone who wants to live and healthy life, uncover their true potential! Pro level support for everyone!
- **How is it different from existing apps like Strava or TrainingPeaks?**
	- Strava only tracks your activities and allows you to share them with your friends. 
	- TrainingPeaks is a great platform to sync training plans to your smartwatches and track your performance, but it requires you to buy static plans and pay for coaches who supports many athletes at the same time. It is not tailored to you and cannot answer your questions or adapt to your life and progress!
- **What does it cost?**
	- 14.99 EUR per month if you commit for a year
	- 19.99 EUR per month otherwise
- **What devices does it work with?**
	- Compatible with all smartphones (Android, Apple) and most smartwatches or connected bands (Garmin, Whoop, Oura Ring)
- **How does it personalize training?**
	- Kinethos reads all your training data and parses it leveraging the latest health and training research to recommend the best approach for you!
- **Does it require a smartwatch or fitness tracker?**
	- It can work without, but the quality of the recommendations will improve with additional data
- **Can it handle injuries or schedule changes?**
	- Yes, if you feel any start of pain or discomfort, you can discuss it with Kinethos who will recommend the best course of action. Sometimes rest is the fastest path toward your goals
- **How does it keep me motivated?**
	- Imagine having a coach dedicated to you 24/7 and who knows everything about your health.
	- Kinethos will reach out to you in the morning to explain your main recovery metrics: sleep quality, Resting Heart Rate, Heart Rate Variability, ... and explain how those reflect your past training and impact your target for the day! Low HRV after a tough interval session: better to take it slightly easier today, go for a 20 min Z2 run and then stretch for 30 min!

## **3. FAQ – Internal (Execution / Product Development)**

- **What problem are we solving?** 
	- leverage detailed problem statement I already wrote
- **Why now?** 
	- Since COVID, health / sport market is booming! Bike sales exploded, more and more people started running: most races such as Marathon or Ultra trails now sell out in couple of hours!
	- AI technology reached the point where it can really support here and people grew comfortable with using it: tech savy people already ask ChatGPT for training plans! But not practical
	- Most company focus on the social / data aspect of sport / training: big market gap on the motivation / coaching side
- **How will it technically integrate with existing platforms (Strava, Garmin, Whoop)?**
	- TBD
- **What are the biggest risks?**
	- Big names like Strava, Garmin or Whoop could block access to their data and develop a similar product
	- AI hallucination could lead to overtraining or injuries: we will need to be very careful with health claims, cannot replace doctor/phisiotherapist. Might blow out and create negative image for our brand
- **What’s the minimum viable product (MVP)?**
	- Simple interface between garmin data collection and AI feeding back training plan and automatically loading it in the app for easy sync with watch
	- At first AI can be a simple general model (Bedrock, Claude, ...) customized with training info
- **What’s the pricing model?** (Subscription, freemium, upsell for premium features.)
	- Subscription model
- **How will we acquire early customers?**
	- I have great market advantage because I am an active member of several running and cycling clubs, known by the community as a strong athlete and successful data professional through my day job at Amazon
	- The initial strategy will be to acquire testers among sport enthusiast in my communities as well as beginners from my friends and family. This will allow me to get early feedback from actual users
	- Another advantage is that Luxembourg market is small but very active, relatively wealthy and health conscious. 
	- Additionally Luxembourg government is very supportive of local startups and ideas such as this one.
	- Also Luxembourg is small enough that it is easy to get media attention
- **How will we ensure accuracy of training recommendations?**
	- Initially we will do things that don't scale (like Airbnb did when they took professional pictures of the first places on the site to help the demand an set standards)
		- use actual coaches to review training plan advices and give feedback to the AI
		- leverage medical professionals for recovery data
		- ...
- **How will we measure impact (e.g., user retention, health improvements)?**
	- We will track the user growth, user retention, number of interaction per user per day, the actual plan adherence: if we recommend to run slowly for longer is the user actually following the changes?
- **What does success look like in 1 year? 3 years?**
	- 1 year: have a working version of the product, captured part of the Luxembourgish enthusiasts market, got support from Luxembourg government and featured in local media
	- 3-years: 
		- Product is very advanced now
		- Allowed us to scale in all english speaking countries 
		- We can see that beginners are creating lasting habits and that athletes follow our plans, ask more and more complex questions to their AI coach
		- Strava/Garmin is interested in buying our product and integrate it in their offering

### Appendix B — Key “easy to forget” fundamentals
- **Hard boundary:** coaching/education, not healthcare.
- **Deletion is real:** revoke tokens, delete user data, confirm completion.
- **Grounding discipline:** only reference data you have; say when you don’t.
- **Fast iteration:** log prompts/outputs, label failures, improve weekly.
