# Brand Answer Auditor — Specification

Status: draft v0.1 (2026-10-31). This file is the source of truth. If the code and this
file disagree, one of them is a bug. Behaviour changes update this file in the same commit.

---

## 1. Problem

People now ask AI assistants things like "What are the best wireless headphones under $200?"
Brands want to know two things about the answers:

1. **Inclusion** — Is my brand mentioned at all? How often, compared with competitors?
2. **Accuracy** — When the assistant talks about my products, are the facts right
   (price, battery life, warranty, and so on)?

**Why repeated runs matter.** AI assistants are not deterministic. The same prompt can
name a brand in one run and leave it out in the next. One run is a sample of one; it
tells you almost nothing. So we ask the same prompt many times and treat inclusion as a
probability: "brand X was named in 14 of 20 runs". We report that rate with a 95% Wilson
confidence interval so the reader can see how much uncertainty is left. With 3 runs the
interval is wide; with 50 it is narrow. Accuracy has the same problem: one answer may be
right and the next one wrong, so we check every answer, not just one.

The service does two jobs:

- **Audit runs**: send shopping prompts to one or two answer models several times, store every
  answer, measure inclusion per brand, and verify the claims in every answer.
- **Verification**: a verification agent (a second AI model with tools) reads one answer,
  pulls out each product claim, and labels it `supported`, `contradicted` or `unknown`
  against a brand fact catalogue.

Every `contradicted` claim goes to a human review queue, because a wrong label in either
direction is costly and a human should confirm it before anyone acts on it.

---

## 2. Scope

### In scope

- HTTP API (FastAPI) described in section 6.
- Audit runs against answer models through official APIs (Google Gemini via `google-genai`,
  OpenAI via `openai`), processed by a separate worker process (6.4) that resumes
  interrupted runs.
- Inclusion measurement with Wilson confidence intervals.
- Verification agent with tool calling, strict output validation and a call limit.
- Human review queue for contradicted claims.
- A brand fact catalogue and prompt list, loaded from strict CSV files by `auditor seed`.
- An offline evaluation harness that scores the verifier against a hand-labelled gold set.
- PostgreSQL 16 storage with Alembic migrations; SQLite for fast tests.
- Docker image, GitHub Actions CI, Fly.io config.

### Out of scope

- Scraping or automating consumer chat apps (ChatGPT web, Gemini app, etc.). We only call
  official model APIs, so results describe the API model, not the consumer app.
- Explaining *why* a brand is missing from an answer.
- Any web UI. The API is the product.
- Editing the catalogue through the API (catalogue changes go through the loader script).
- Per-client catalogues (v1 has one shared catalogue).
- Separate queue services (Celery, Redis). The worker uses the PostgreSQL table as its
  queue (6.4).

---

## 3. Label rules

These rules are written for both the verification agent and the humans who label the
gold evaluation set. Both must follow the same rules, or the evaluation means nothing.

### 3.1 What is a claim

A **claim** is a sentence or clause in the answer that states a **checkable fact** about a
**named product** of a brand in the catalogue.

Checkable fact types in v1 (closed list):

| attribute          | example                                         |
|--------------------|-------------------------------------------------|
| `price`            | "The Zentro Air 2 costs $149."                  |
| `battery`          | "It lasts about 30 hours on a charge."          |
| `feature`          | "It has active noise cancelling."               |
| `warranty`         | "Zentro gives a 2-year warranty."               |
| `water_resistance` | "It is rated IPX4."                             |
| `release_year`     | "It came out in 2024."                          |
| `comparison`       | "It lasts longer than the Kova Pulse."          |

Rules:

- **Opinions are not claims.** "Great sound", "best value", "I'd recommend it" are skipped.
- **Only catalogue brands.** Statements about brands that are not in the catalogue are
  skipped. A comparison between a catalogue product and another product *is* a claim
  (the catalogue brand is the subject).
- **Brand-wide statements** ("all Zentro headphones have a 2-year warranty") count as
  claims about that brand; the product is left empty.
- **One fact per claim where possible.** Quote the smallest clause that contains the fact.
  If two facts cannot be separated into different quotes, one claim may hold both; then
  the label rules below apply to every part.
- The claim is identified by an **exact quote** from the answer text (see 4.4).

### 3.2 Labels

| label          | meaning |
|----------------|---------|
| `supported`    | Catalogue facts confirm **every** material part of the claim. |
| `contradicted` | At least one catalogue fact **explicitly conflicts** with a material part of the claim. |
| `unknown`      | The catalogue cannot decide. **Missing evidence is not a contradiction.** |

If one part is contradicted and another is unknown, the label is `contradicted`.

### 3.3 Material qualifiers

A qualifier is **material** if changing it could change whether the claim is true.
These are always material:

- **Market** — "$149 in the US" is a different claim from "$149 in the UK".
- **Currency** — "$149" cannot be confirmed or refuted by a fact in GBP alone.
- **Units** — "30 m water resistance" is not "30 ft". Values may be compared after an
  exact unit conversion in the same dimension (minutes ↔ hours).
- **Model** — "Zentro Air 2" is not "Zentro Air 2 Pro".
- **Conditions** — "30 hours with ANC off" is not "30 hours with ANC on".
- **Comparison direction** — "X lasts longer than Y" is the opposite of "Y lasts longer than X".

How qualifiers are applied:

- **Market not stated in the claim.** Use the market given in the request (if any). If no
  market is known and the facts differ by market, the label is `unknown`.
- **Currency with no matching fact.** If the claim's currency has no fact, the label is
  `unknown`, not `contradicted`.
- **Condition not stated in the claim.** If the claim's value matches the fact for at least
  one stated condition, it is `supported` (cite that fact; the rationale names the
  condition). If it matches none, it is `contradicted`.
- **Hedged numbers** ("about 30 hours", "around $150"): `supported` if the fact is within
  ±5% of the stated number; otherwise `contradicted`. Unhedged numbers must match exactly
  (after exact unit conversion).
- **Comparisons** need facts for both sides. If either side has no fact, the label is `unknown`.

### 3.4 Citations

- `supported` and `contradicted` must cite **at least one** fact ID.
- `unknown` may cite the facts that were checked, or none.
- **Every cited fact ID must have been returned by a tool call in this answer's
  conversation.** A model may not cite a fact it never saw.

---

## 4. Verification agent contract

### 4.1 Inputs

- The answer text (1 to 20,000 characters).
- Optional `market` (for example `US`), used by the rules in 3.3.

The answer text is **untrusted input**. It is placed inside `<ai_answer>` tags in the user
message, and the model is told it is data, not instructions. A `</ai_answer>` inside the
answer is neutralised so the answer cannot close the tag early (quotes are still matched
against the original text). The tools are read-only, so the worst a malicious answer can
do is cause wrong labels, which the review queue and the evaluation harness are there to
catch.

The system prompt is versioned. `v1` states the rules in section 3; `v2` is `v1` plus
exactly one addition, a qualifier checklist (market and currency, conditions, comparisons,
units and numbers, similar models), so any score change between them has one cause.
Every result records its prompt version.

### 4.2 Tools

| tool | kind | input | returns |
|------|------|-------|---------|
| `list_known_brands()` | read-only | none | list of `{brand_id, name, aliases}` |
| `get_brand_facts(brand_id)` | read-only | a brand ID | list of facts for that brand (see 4.6) |
| `submit_claims(claims)` | final answer | list of claims (4.3) | `{accepted: true}` or `{accepted: false, problems: [...]}` |

- Read-only tools never change the database.
- Tool problems come back to the model as an error **result** (`{"error": "..."}`), never as
  an exception: an unknown tool name, arguments that are not a JSON object, unexpected or
  missing arguments, an unknown `brand_id`, or even a crash inside the tool. The model can
  correct itself on its next turn. Each such error is counted (see 4.7).
- The model may request several read-only tools in one response; code runs them all, in
  order, and returns all results together.
- `submit_claims` must be the **only** tool call in its response. If it is mixed with
  other calls, that is a validation problem (see 4.5).

### 4.3 `submit_claims` input

Each claim:

| field | type | notes |
|-------|------|-------|
| `quote` | string | Exact text copied from the answer. |
| `brand_id` | string | A catalogue brand ID. |
| `product` | string or null | Product/model name as written in the catalogue; null for brand-wide claims. |
| `attribute` | enum | One of the attributes in 3.1. |
| `label` | enum | `supported`, `contradicted`, `unknown`. |
| `fact_ids` | list of strings | Cited facts (rules in 3.4). |
| `rationale` | string, ≤ 300 chars | One or two sentences, for the human reviewer. |

Unexpected fields are rejected. An empty list is valid: it means the answer has no claims.

### 4.4 The model quotes, the code computes offsets

The model **never** returns character positions. Models are bad at counting characters.
The model returns an exact quote; code finds it in the answer and stores:

- `start` — index of the first character (inclusive),
- `end` — index after the last character (exclusive),

using Python string indices, so `answer_text[start:end] == quote` is always true for a
saved claim. Matching is exact and case-sensitive. No normalisation.

**Repeated text.** If the quote appears more than once, code picks an occurrence no earlier
claim has used, preferring the first one at or after the end of the previous claim
(models list claims in reading order). If every occurrence is already used, that is a
validation problem.

### 4.5 Validation of `submit_claims`

Code checks every submission and collects **all** problems in one pass (the model has
at most one repair turn, so it must see them all at once). Each becomes one plain-English
line, for example `claim 2: quote not found in the answer text`.

1. The input matches the schema in 4.3 (Pydantic) and is a JSON object.
2. `quote` is not empty and appears in the answer.
3. Some occurrence of `quote` is not already used by an earlier claim (4.4).
4. `brand_id` exists in the catalogue.
5. `supported` and `contradicted` claims cite at least one fact ID.
6. Every cited fact ID was returned by `get_brand_facts` in this conversation.
7. `submit_claims` was the only tool call in that response.

### 4.6 Fact shape returned by `get_brand_facts`

`{fact_id, brand_id, product, attribute, value, unit, market, conditions, valid_from, source_url}`.
`product`, `unit`, `market`, `conditions`, `valid_from` and `source_url` may be null.

Fact attributes and their rules (checked by the loader):

| attribute | value | unit | other rules |
|-----------|-------|------|-------------|
| `price` | positive number | the market's currency (`IN` → `INR`, `US` → `USD`) | market required |
| `battery` | positive number | `hours` | conditions required, e.g. "earbuds only, ANC off" |
| `warranty` | whole number > 0 | `months` | market required |
| `anc` | `yes` or `no` | none | |
| `water_resistance` | IP code such as `IPX4`, `IP67` | none | |
| `release_year` | year 2000–2100 | none | |

There is no separate currency field: a price's `unit` is its currency.

**Facts are immutable**: a changed fact gets a new ID. The loader refuses to change the
content of an existing fact ID, so old citations always point to what the model saw.

### 4.7 The loop

```
turn = 0
while turn < max_turns:
    turn += 1
    response = model(conversation, tools)        # with timeout and retries (4.8)
    if response has no tool call:
        append a nudge ("reply with a tool call ..."), continue
    if response calls submit_claims:
        problems = validate(...)                 # all problems at once (4.5)
        if no problems: return success           # the caller saves it (4.9)
        append {accepted: false, problems}, continue
    run the read-only tool calls, append their results, continue
out of turns:
    if no submission was ever attempted and some tool calls failed: fail as "tool"
    otherwise: fail as "prompt"
```

The verifier never raises, with one exception: a `config` error (missing key or model,
credentials rejected) is raised to the caller, because it would fail every answer the
same way and the whole run should stop. Any other unexpected exception becomes a `code`
failure, so one answer can never crash a run. Results carry: ok, claims, model, prompt
version, turns used, tokens, latency, error type and detail, `timed_out`, and the full
conversation (for debugging).

- **At most 4 model calls per answer** (`AGENT_MAX_TURNS`, default 4, may be lowered but
  never raised above 4). A typical answer needs 3: list brands, fetch facts
  (several brands in one response), submit. The 4th is a chance to fix a rejected submission.
- On the **4th call**, only `submit_claims` is offered and the model is required to call it.
- A "model call" is one logical request. Retries of the same request (4.8) do not count as
  extra calls.
- Use the lowest-randomness settings the model supports (for example temperature 0) and
  record the provider, model name and settings on the answer.

### 4.8 Timeouts and retries

- Every model request has a timeout (`LLM_TIMEOUT_SECONDS`, default 30).
- Retry **only** on: rate limits (HTTP 429), server errors (HTTP 5xx), timeouts,
  connection errors.
- Never retry other errors (for example 400, 401, 403, 404); they fail at once.
- Exponential backoff: up to `LLM_MAX_RETRIES` retries (default 3) after the first
  attempt, waiting 1 s, 2 s, 4 s, ... plus a random jitter of 0–0.5 s.
- The sleep function is injectable, so tests run instantly.
- The SDKs' own retries are turned off (OpenAI `max_retries=0`, Gemini retry `attempts=1`),
  so this policy is the only retry loop and latency numbers include every attempt.
- Each provider's errors are mapped to four kinds: transient (retried), timeout (a
  transient error that also sets `timed_out`), permanent (not retried), and config
  (401/403 or missing key/model; not retried). For Gemini, timeouts and network failures
  arrive as raw `httpx`/`httpx2` exceptions and are mapped the same way.
- The same policy applies to the answer models in audit runs.

### 4.9 Saving: all or nothing

- On success, the answer's claims, their offsets, labels, cited fact IDs and one review
  item per `contradicted` claim are saved in **one database transaction**.
- On failure, **no claims and no review items** are saved. The answer row records
  `status = verification_failed` and the `error_type`, so failures can be counted.
- The answer row also stores the verifier provider and model, prompt version, turns
  used, latency, `timed_out`, and token usage for both phases (`usage`:
  `{"generation": {...}, "verification": {...}}` with input/output/thinking counts).
  Token counts come from the provider's usage data; if the provider gives none, they are
  stored as null, never estimated. Gemini "thinking" tokens are billed as output, so they
  count toward output tokens and are also stored separately.

---

## 5. Error types

Every failed answer has exactly one error type.

| type       | meaning |
|------------|---------|
| `provider` | The model API failed: a retryable error that survived all retries, a non-retryable provider error, or an empty/blocked response. |
| `prompt`   | The model replied but did not produce a valid `submit_claims` within the turn limit (invalid submissions, or no tool calls at all). |
| `tool`     | The turn limit was reached without any submission while tool calls kept failing (unknown tool, bad arguments, unknown brand, or a tool crash). |
| `data`     | Stored data is invalid or inconsistent (for example a malformed catalogue fact). |
| `config`   | Settings are missing or wrong: missing API key, unknown provider, or credentials rejected by the provider (401/403). |
| `code`     | An unexpected bug in our code: any exception we did not classify. |

A single failed tool call is not a failure: it is returned to the model as an error
result (4.2) and the model may recover. Only running out of turns turns it into `tool`.
`config` errors are raised to the caller and stop the run (4.7); `timed_out` is set on a
`provider` failure whose last attempt timed out.

---

## 6. API

### 6.1 Authentication and isolation

- Every `/v1/*` endpoint needs `Authorization: Bearer <api-key>`. `/healthz` does not.
- Keys are created with `auditor create-api-key <name>`, which prints the key **once**.
  A key is `baa_` + `secrets.token_urlsafe(32)` (256 random bits). The prefix lets secret
  scanners recognise a leaked key. Only the **SHA-256 hash** is stored; a request's key
  is hashed and looked up. A fast hash is enough because the key is random, not chosen
  by a person. Plain keys are never stored or logged.
- Missing, malformed or unknown key → `401` with `WWW-Authenticate: Bearer`. Auth is
  checked before the request body.
- Each audit run, answer and review item belongs to one client. Asking for another
  client's resource returns `404` (not `403`), so clients cannot learn what exists.

### 6.2 Error body

Every error, including validation errors and unknown routes, uses one shape:

```json
{"error": {"code": "not_found", "message": "audit run not found"}}
```

Validation errors (`422`, code `validation_error`) add `details` (field location and
message). Verification failures add `error_type` (section 5) and `answer_id`. A `500`
gives a generic message; the details stay in the stored answer.

All timestamps in responses are UTC with an explicit offset.

### 6.3 Endpoints

| method & path | purpose | success | errors |
|---------------|---------|---------|--------|
| `GET /healthz` | Liveness plus a database ping. | `200 {"status": "ok"}` | `503 {"status": "unavailable"}` database unreachable |
| `POST /v1/verify` | Verify one answer text now (synchronous). Body: `text` (1–20,000 chars), optional `market`, `prompt_version` (`v1`/`v2`). The answer is saved **before** the model is called, so failed attempts are stored too. | `200` answer with claims and exchanges | `401`; `422` invalid body; `502` provider error (`provider_error`) or invalid model output (`invalid_model_output`, from `prompt` or `tool`); `504` provider timeout; `503` verifier not configured (`config`); `500` `code` or `data`. Every verification error body carries `answer_id` |
| `POST /v1/audit-runs` | Queue an audit run (body = run config, 6.4). Needs `Idempotency-Key` header (1–200 chars). | `202` new run, with `Location: /v1/audit-runs/{id}`; `200` + `Idempotent-Replayed: true` for the same key and same body | `400` missing `Idempotency-Key`; `401`; `409` same key with a different body; `422` invalid run config (including `max_model_calls` above 5,000) or no prompts match (`no_matching_prompts`) |
| `GET /v1/audit-runs/{id}` | Run status, config, model calls, metrics (section 7), failure reason. | `200` | `401`; `404`; `422` malformed ID |
| `GET /v1/answers/{id}` | One answer: text, status, error, brands mentioned, claims with offsets, labels, fact IDs, rationale, usage, and the verifier conversation (`exchanges`). | `200` | `401`; `404`; `422` malformed ID |
| `GET /v1/review-items?status=` | List review items with their claims. `status` is `open`, `confirmed` or `dismissed` (optional). `limit` (default 50, max 200) and `offset`. | `200` list | `401`; `422` invalid query |
| `PATCH /v1/review-items/{id}` | Record a decision. Body: `{"decision": "confirmed" \| "dismissed", "note": "..."}`. | `200` updated item | `401`; `404`; `409` already decided (a decision is final, so the audit trail cannot be rewritten); `422` invalid body |

The canonical request body for idempotency is the validated run config with defaults
filled in, serialised as JSON with sorted keys. So two bodies that mean the same thing
(different key order, or a default written out) count as the same body. A race between
two requests with the same key is settled by the unique constraint: the loser rolls
back and replays the winner's run.

Run the API with `uvicorn auditor.api.app:create_app --factory`. The verifier client is
built per request, so missing verifier settings give `503` on `/v1/verify` instead of
stopping the API from starting.

### 6.4 Audit runs

**Run config** (stored on the run as JSON, validated by `RunConfig`):

```json
{
  "category": "earbuds",
  "prompt_ids": ["p02", "p03"],
  "answer_providers": ["gemini", "openai"],
  "repeats": 3,
  "agent_version": "v1",
  "max_model_calls": 500
}
```

| field | rule | why |
|-------|------|-----|
| `category` | required; prompts are selected by `prompts.category` | a run audits one product area |
| `prompt_ids` | optional; 1–50 unique IDs, all in that category | narrow a run to some prompts |
| `answer_providers` | 1–2 unique of `gemini`, `openai` | compare assistants, keep cost bounded |
| `repeats` | 1–5, default 3 | stability without a large bill |
| `agent_version` | `v1` or `v2`, default `v1` | which system prompt verifies (4.1) |
| `max_model_calls` | 1–5,000, default 500 | hard budget (below) |

Each answer provider writes answers with its own model setting (`GEMINI_ANSWER_MODEL`,
`OPENAI_ANSWER_MODEL`); the verifier uses `VERIFIER_PROVIDER` / `VERIFIER_MODEL`.

**Idempotency** (`POST /v1/audit-runs`):

- The key is scoped to the client. The server stores the key with a SHA-256 hash of the
  request body.
- Same key + same body → return the existing run; nothing new is started.
- Same key + different body → `409`.
- Two requests racing with the same key: a unique database constraint lets only one win;
  the other returns the winner's run.

**Worker.** Runs are processed by `auditor worker`, a separate process. The `audit_runs`
table is the queue; no Celery or Redis.

- **Claiming:** a worker takes the oldest `queued` run with
  `SELECT ... FOR UPDATE SKIP LOCKED` and marks it `running` in the same transaction.
  Two workers asking at once get different runs, and neither waits for the other.
- **Heartbeat:** `heartbeat_at` is updated after every answer. Before claiming, a worker
  puts any `running` run whose heartbeat is older than `STALE_RUN_SECONDS` (default 900)
  back to `queued`: its worker has died.
- **Startup check:** the worker builds the verifier client before taking work, so a
  missing provider, model or key stops it at once.
- **Shutdown:** on SIGTERM or Ctrl+C, the current run is handed back to `queued` before
  its next model call, and the worker exits.

**Processing a run** (`process_run`):

1. Select the prompts (unknown category or prompt ID → run `failed`, "data: ...").
   Build every model client first (missing key or model → run `failed`, "config: ...").
2. **Collect:** for each prompt × provider × repeat, ask the answer model the prompt with
   no system prompt (we audit default behaviour), with timeout and retries (4.8). Detect
   brand mentions (7.1). Commit each answer on its own. A slot that already has an
   answer row (any status) is skipped, so a resumed run never pays for an answer twice.
   A provider failure is saved as `generation_failed`; the run goes on.
3. **Verify:** each `pending` answer goes through the agent (section 4), against one
   in-memory snapshot of the catalogue for the whole run. The result is saved in one
   transaction (4.9).
4. **Finish:** compute the run metrics (section 7) from the stored rows, store them on
   the run, and set the final status.

No database transaction is held open during a model call.

**Budget.** `model_calls` on the run counts logical model calls (retries are attempts of
one call and are not counted). Before each collection call it must stay within
`max_model_calls`. Before verifying an answer, the worst case (`AGENT_MAX_TURNS`) is
reserved; the unused turns are refunded afterwards. If the next call does not fit, the
run stops with status `partial` and metrics for what was done.

**Run status:** `queued` → `running` → `completed` (every answer attempted, even if some
failed), `partial` (budget reached), or `failed` (run-level problem; `failure_reason`
starts with `config:`, `data:` or `code:`). A `config` failure is logged as one line, a
`code` failure with its traceback.

**Answer status:**

| status | meaning | counts for inclusion? | counts for accuracy? |
|--------|---------|-----------------------|----------------------|
| `pending` | answer text saved, not verified yet | yes | no |
| `generation_failed` | the answer model gave no answer | no | no |
| `verification_failed` | answer text saved, verification failed | yes | no |
| `verified` | answer text and claims saved | yes | yes |

### 6.5 Configuration (environment variables)

All config comes from environment variables (or a local `.env` file), read with
pydantic-settings. An empty value means "not set". Only `DATABASE_URL` is needed to start;
provider settings are checked when a model client is built, and a missing key or model
fails with a `config` error. `.env.example` lists every variable.

| variable | required | notes |
|----------|----------|-------|
| `DATABASE_URL` | yes | `postgresql+psycopg://...` in production; `sqlite:///...` for local use. |
| `GEMINI_API_KEY` | if Gemini is used | Held as a secret; never printed. |
| `OPENAI_API_KEY` | if OpenAI is used | Held as a secret; never printed. |
| `VERIFIER_PROVIDER` | to verify | `gemini` or `openai`. |
| `VERIFIER_MODEL` | to verify | Model ID. Empty by default; no model ID is hardcoded. |
| `GEMINI_ANSWER_MODEL` | for Gemini runs | The model that writes audited answers. Empty by default. |
| `OPENAI_ANSWER_MODEL` | for OpenAI runs | The model that writes audited answers. Empty by default. |
| `WORKER_POLL_SECONDS` | no | Default 5. How often an idle worker looks for queued runs. |
| `STALE_RUN_SECONDS` | no | Default 900. A running run with an older heartbeat is requeued. |
| `LLM_TIMEOUT_SECONDS` | no | Default 30. |
| `LLM_MAX_RETRIES` | no | Default 3. |
| `AGENT_MAX_TURNS` | no | Default 4, allowed 1–4. |
| `LLM_TEMPERATURE` | no | Default 0. `none` means the parameter is not sent (some models reject it). |
| `INPUT_TOKEN_PRICE_PER_MILLION` | no | USD. Cost is reported only when both prices are set; otherwise null. |
| `OUTPUT_TOKEN_PRICE_PER_MILLION` | no | USD. |
| `LOG_LEVEL` | no | Default `INFO`. |

### 6.6 Storage

PostgreSQL 16 in production, SQLite in fast tests, schema managed by Alembic (`migrations/`).
Fixed value sets (statuses, labels, error types, attributes, providers) are Python
`StrEnum`s stored as plain strings, so adding a value needs no database type change.

| table | holds |
|-------|-------|
| `brands` | brand ID, name (shared catalogue) |
| `brand_aliases` | other names a brand appears under; unique ignoring case across all brands |
| `brand_facts` | the facts in 4.6; immutable |
| `prompts` | prompt ID, category, text, market |
| `api_clients` | client name and the SHA-256 hash of its API key (one key per client in v1) |
| `audit_runs` | client, idempotency key + request hash (unique per client), status, run config (JSON), `model_calls` / `max_model_calls`, metrics (JSON), failure reason, created/started/heartbeat/finished times |
| `answers` | client, run (empty for `/v1/verify`), prompt, provider/model, repeat index, market, text, status, error type and message, brands mentioned, verifier provider/model, prompt version, turns, latency, `timed_out`, token usage (JSON), verifier conversation (`exchanges`, JSON); unique on (run, prompt, model, repeat index) |
| `claims` | answer, quote, start/end offsets, brand, product, attribute, label, cited fact IDs, rationale |
| `review_items` | client, claim (one item per claim), status, note, timestamps |

Model-call metadata is kept per answer (4.9), not per call: the metrics in section 7
only need per-answer totals.

Logs never contain API keys, `Authorization` headers or provider credentials. Answer
text and prompts are not logged at `INFO` level.

---

## 7. Metrics

All metrics are **computed from stored rows** when requested or when the evaluation
harness runs. No metric is typed in by hand or hardcoded. When a denominator is 0 the
metric is reported as `null`, never as 0 or 1.

### 7.1 Inclusion

- **Mention detection is done by code, not by a model.** A brand is mentioned if its name
  or any alias appears in the answer as a whole word, ignoring case. This is cheap,
  deterministic and easy to explain.
- For each catalogue brand: `k` = answers that mention it, `n` = answers with text
  (`pending`, `verified` or `verification_failed`; mention detection does not need
  verification). Inclusion rate `p = k / n`.
- Reported per answer model and for all models together, with `k`, `n`, `p` and the 95%
  Wilson interval.

Wilson score interval, `z = 1.959964` (95%):

```
centre     = (p + z²/(2n)) / (1 + z²/n)
half_width = (z / (1 + z²/n)) * sqrt( p(1-p)/n + z²/(4n²) )
interval   = [centre - half_width, centre + half_width]
```

Why Wilson and not the simple `p ± 1.96·sqrt(p(1-p)/n)`: the simple version breaks for
small `n` and for `p` near 0 or 1 (for example, 0 of 10 gives an interval of [0, 0],
which claims false certainty). Wilson stays inside [0, 1] and is honest at small `n`.

### 7.2 Claim label shares

For a run: counts of `supported`, `contradicted` and `unknown` claims from `verified`
answers, and each count divided by the total number of claims. Counts are always shown
next to shares.

The run metrics stored on a finished run also include: answer counts by status, failed
answers by error type, token totals per phase (generation, verification, total), model
calls used against the budget, and `cost_usd` — computed from reported tokens and
`INPUT_TOKEN_PRICE_PER_MILLION` / `OUTPUT_TOKEN_PRICE_PER_MILLION`, and `null` unless
both prices are set and tokens were reported.

### 7.3 Evaluation metrics (offline harness)

The harness (`auditor eval`) runs the verifier on a gold set: synthetic answers with
hand-labelled claims written using the rules in section 3 (`data/demo/eval_set.json`).

**Dataset.** Loading is strict and lists every problem: invalid JSON, unknown fields, bad
labels, a decisive label without facts, duplicate answer IDs, unknown prompt IDs, quotes
that cannot be located, unknown brands and unknown fact IDs. Gold offsets are computed
with the **same** `locate_quote` the validator uses (4.4), so a repeated sentence maps to
the same occurrence for gold and prediction. Selecting answers by ID rejects unknown
IDs. The dataset's fingerprint is the SHA-256 of its canonical JSON (sorted keys, no
whitespace), so formatting and line endings do not change it.

**Scoring** (micro-averaged: totals are summed over all answers before dividing):

- **Exact-span extraction P/R/F1.** A predicted claim matches a gold claim only if `start`
  and `end` are both equal. Precision = matches / predicted claims; recall = matches /
  gold claims; F1 = 2PR / (P + R).
- **Joint P/R/F1 (span + label).** Same as above, but a match also needs the same label.
- **Recall on contradicted.** Of gold `contradicted` claims, the share predicted with the
  exact span **and** the label `contradicted`. This is the most important number: a missed
  contradiction never reaches the review queue.
- A **failed answer predicts nothing**, so its gold claims count as missed.
- For error analysis the report lists, per answer and repeat: missed gold claims,
  wrong-label matches and unmatched predictions.

**Runs.** One eval = one split × `R` repeats (default 3), because one run could be lucky.

- Each metric is reported as **mean, min and max** over the repeats.
- **Failure rate**: failed answers / (answers × repeats), overall and per error type.
- **Consistency**: share of answers that got exactly the same set of
  `(start, end, label)` in every repeat (a failure is its own outcome); `null` for one repeat.
- **Latency p50/p95** (nearest-rank) of whole-answer verification time, including retries.
- **Tokens** (totals and mean per answer) from provider usage data; **cost** only when
  both prices are set.

**Honesty rules.**

- Each report records the date, git commit (and whether there were uncommitted changes),
  provider, model, prompt version, settings, dataset version, fingerprint, split and
  answer IDs.
- `is_real_run` is decided from the client's type (a Gemini or OpenAI client), never
  passed in, so a fake client cannot produce a "real" report. A fake run's Markdown
  starts with `NOT A REAL RESULT`.
- Reports are written to `reports/`, which git ignores. No result number is committed;
  README numbers may only be copied from a generated real report.

**Comparing** (`auditor compare BASELINE CANDIDATE --max-drop 0.02`): refused (exit 2) if
either report is not a real run, or the dataset fingerprint, split or answer IDs differ.
Fails (exit 1) if the mean joint F1 or the mean contradicted recall drops by more than
`max_drop`; otherwise passes (exit 0) and prints every metric's change.

---

## 8. Acceptance criteria

- [ ] `ruff check .`, `ruff format --check .` and `pytest` pass locally and in GitHub Actions.
- [ ] No test calls a real model API; model clients are injected and tests use a scripted fake client.
- [ ] Alembic migrations upgrade an empty database on PostgreSQL 16 (in CI) and on SQLite.
- [ ] Every row of the endpoint table (6.3) has a test for its success code and each listed error code.
- [ ] Requests without a valid key get `401`; another client's resource gets `404`.
- [ ] Only SHA-256 hashes of API keys are stored; plain keys never appear in the database or logs.
- [ ] For every saved claim, `answer_text[start:end] == quote`.
- [ ] Each validation rule in 4.5 has a test that triggers it and checks the problem message.
- [ ] A fake model that submits an invalid list and then a valid one ends with the valid claims saved.
- [ ] A fake model that never submits a valid list makes exactly 4 calls, fails as `prompt`, and saves no claims or review items.
- [ ] On the 4th call only `submit_claims` is offered.
- [ ] Retries happen only for 429, 5xx, timeouts and connection errors, with 1 s / 2 s / 4 s backoff (checked with a fake sleep); other errors fail on the first attempt.
- [ ] Each of the six error types (section 5) can be produced in a test and is stored on the answer.
- [ ] Every `contradicted` claim creates exactly one `open` review item in the same transaction.
- [ ] `PATCH` on a resolved review item returns `409`.
- [ ] Same `Idempotency-Key` + same body returns the same run and creates no new answers; a different body returns `409`.
- [ ] The Wilson function matches values worked out from the formula in 7.1, including `k = 0` and `k = n`.
- [ ] Inclusion uses only `verified` + `verification_failed` answers as `n`.
- [ ] The eval harness computes every metric in 7.3 from model outputs and the gold set and writes a report with the metadata listed there.
- [ ] Docker image builds and starts; `GET /healthz` returns `200`.
- [ ] `fly.toml` contains no secrets; secrets are set with `fly secrets`.
- [ ] The catalogue loader rejects bad CSV (wrong header, wrong field count, unknown brand, duplicate ID or alias, value that breaks the rules in 4.6) with the file name and line number.
- [ ] Seeding twice inserts nothing the second time; a seed that would change an existing fact is refused.
- [ ] The SQL and in-memory catalogues return identical brands and facts.
- [ ] `auditor check-data` passes: every gold quote can be located (with the validator's `locate_quote`) and every cited fact ID exists; a broken gold file is rejected with every problem listed.
- [ ] Scoring maths matches a hand-worked example; a failed answer predicts nothing.
- [ ] A fake client's eval report has `is_real_run: false` and its Markdown starts with `NOT A REAL RESULT`; `compare` refuses it, refuses different datasets/splits, and detects a regression.
- [ ] A submission citing a fact ID the agent never looked up is rejected, and the model can repair it on the next turn.
- [ ] A repeated sentence quoted by two claims gets two different spans; a third copy is rejected.
- [ ] All validation problems in one submission are returned together.
- [ ] Failed tool calls until the turn limit end as `tool`; invalid output or no tool calls end as `prompt`; an unexpected exception ends as `code`; a config error is raised.
- [ ] The hand-written tool JSON schemas match the Pydantic argument models and contain no `$ref`.
- [ ] Two workers claiming at the same time get different runs (`SKIP LOCKED`, PostgreSQL test).
- [ ] A `running` run with a stale heartbeat is requeued; a stopped run resumes without repeating any answer-model call.
- [ ] The budget is checked before every call; verification reserves `AGENT_MAX_TURNS` and refunds unused turns; running out ends the run as `partial`.
- [ ] An unknown category fails the run with `data: ...`; a missing key or model fails it with `config: ...` (no traceback); an unexpected exception with `code: ...`.
- [ ] Run metrics (inclusion with Wilson CI per model and overall, label counts and shares, errors by type, tokens, cost only when prices are set) are computed from stored rows.
- [ ] Responses use one error shape; `401` carries `WWW-Authenticate: Bearer`.
- [ ] `/v1/verify` maps failures to `502` / `504` / `503` / `500`, stores the failed attempt, and returns its `answer_id`.
- [ ] Idempotency: same key + same canonical body replays (`200`, `Idempotent-Replayed`); a different body is `409`; another client's identical key creates its own run; a lost race returns the winner.
- [ ] A reviewed item cannot be decided twice (`409`).
- [ ] SPEC.md matches the implemented behaviour.

---

## 9. Demo data

All brands, products and facts in this repository are **fictional**, and every fact is
**synthetic**. They exist only for tests, demos and the evaluation gold set. They say
nothing about any real company or product. Any resemblance to a real brand name is
accidental.

`data/demo/` holds 6 fictional earbud brands (Aurelyn, Brisalo, Kovalt, Nimbrex, Tavora,
Zentro) with aliases, their facts for markets `IN` and `US`, 6 prompts, and
`eval_set.json`: 16 hand-written AI-style answers (12 `dev`, 4 `holdout`) with gold claims
(exact quote, label, cited fact IDs). The answers include market, condition, comparison,
similar-model, currency and missing-evidence traps. The `holdout` answers are only scored
at the end, never used to tune prompts.
