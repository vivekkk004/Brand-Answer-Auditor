# Brand Answer Auditor

A service that audits what AI assistants say about brands.

1. **Inclusion** — how often each brand is named when shopping prompts are asked again and
   again, with a 95% Wilson confidence interval.
2. **Accuracy** — a verification agent checks each product claim in an answer against a
   brand fact catalogue and labels it `supported`, `contradicted` or `unknown`.
   Every `contradicted` claim goes to a human review queue.

The full behaviour is specified in [SPEC.md](SPEC.md); the code must match it.

> **Status:** the pipeline, API, worker, eval harness and web UI are built and tested with
> fake model clients. **No live eval has been run yet, so there are no accuracy results.**
> All brands and facts in `data/demo/` are fictional.

## How it works

```
POST /v1/audit-runs ──► audit_runs table (queue) ──► worker
                                                     │ 1. collect: prompt × provider × repeat
                                                     │    → answer model (Gemini / OpenAI / Groq)
                                                     │    → brand mentions found by code
                                                     │ 2. verify: agent with 3 tools
                                                     │    list_known_brands, get_brand_facts,
                                                     │    submit_claims (max 4 model calls;
                                                     │    optional fallback verifier)
                                                     │ 3. metrics from stored rows
                                                     ▼
                     answers, claims, review items, run metrics (PostgreSQL)
```

- **Repeated runs** because model answers are random: inclusion is a probability, reported
  as `k / n` with a Wilson interval.
- **The model quotes, code computes offsets.** Claims are exact quotes; code finds their
  character positions and checks every citation. A fact may only be cited if a tool
  returned it in that conversation.
- **Strict validation with one repair turn.** All problems are sent back at once; the last
  turn forces `submit_claims`. Nothing is saved unless the whole answer passes.
- **Typed failures:** `provider`, `prompt`, `tool`, `data`, `config`, `code`.
- **Retries** only for 429 / 5xx / timeouts / connection errors, with exponential backoff.
- **Worker** claims runs with `SELECT ... FOR UPDATE SKIP LOCKED`, commits every answer, and
  resumes after a crash without paying for an answer twice. A model-call budget stops a
  run as `partial`.

## Quick start (local, Python 3.12)

```
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"      # Windows
# .venv/bin/python -m pip install -e ".[dev]"         # Linux / macOS

copy .env.example .env      # then set DATABASE_URL, keys and model IDs
alembic upgrade head
auditor seed                # fictional demo catalogue and prompts
auditor create-api-key me   # prints an API key once
uvicorn auditor.api.app:create_app --factory
auditor worker              # in a second terminal
```

Or with Docker:

```
docker compose up --build
docker compose run --rm api auditor seed
docker compose run --rm api auditor create-api-key me
```

Checks used for every change:

```
ruff check .
ruff format --check .
pytest
```

## Web UI

A React app in `frontend/` (Redux Toolkit, React Router, Tailwind CSS). It only calls the
public API below; the key is kept in the browser tab's `sessionStorage`.

- **Landing page** — what the service does, how it works, how it stays reliable.
- **Overview** — API health, open review items, recent runs.
- **Audit runs** — list, filter, queue a new run (idempotent), and a detail page that
  refreshes while the run is queued or running, then shows inclusion with Wilson intervals,
  label shares, failures by type, tokens and cost.
- **Verify answer** — check one answer now; failed attempts link to the saved answer.
- **Answer** — the text with claims highlighted by label, cited fact IDs, and the agent's
  full conversation (every tool call and result).
- **Review queue** — confirm or dismiss contradicted claims, once.

```
cd frontend
npm install
npm run dev        # http://localhost:5173 (API on :8000; /v1 and /healthz are proxied)
```

## API

All `/v1/*` endpoints need `Authorization: Bearer <key>`. Errors use one shape:
`{"error": {"code": "...", "message": "..."}}`. Another client's IDs return `404`.

| method & path | what it does | success | main errors |
|---------------|--------------|---------|-------------|
| `GET /healthz` | Liveness + database ping | `200` | `503` |
| `POST /v1/verify` | Verify one answer text now | `200` | `502`, `504`, `503`, `500` (with `answer_id`) |
| `POST /v1/audit-runs` | Queue a run; needs `Idempotency-Key` | `202` (+ `Location`), `200` replay | `400`, `409`, `422` |
| `GET /v1/audit-runs?status=` | List my runs, newest first (`limit`, `offset`) | `200` | `422` |
| `GET /v1/audit-runs/{id}` | Status, config, metrics | `200` | `404` |
| `GET /v1/answers/{id}` | Answer, claims, agent conversation | `200` | `404` |
| `GET /v1/review-items?status=` | Review queue | `200` | `422` |
| `PATCH /v1/review-items/{id}` | Confirm or dismiss (once) | `200` | `404`, `409` |

Example run request:

```
curl -X POST http://localhost:8000/v1/audit-runs \
  -H "Authorization: Bearer $KEY" -H "Idempotency-Key: run-1" \
  -H "Content-Type: application/json" \
  -d '{"category": "earbuds", "answer_providers": ["gemini"], "repeats": 3}'
```

## Evals

The eval set (`data/demo/eval_set.json`) has 16 hand-written answers (12 `dev`, 4
`holdout`) with gold claims, including market, condition, comparison, similar-model,
currency and missing-evidence traps.

```
auditor check-data                                   # data is consistent (free)
auditor eval --split dev --repeats 3 --prompt-version v1   # LIVE: calls the model, costs money
auditor compare reports/BASE.json reports/NEW.json --max-drop 0.02
```

Reports go to `reports/` (git-ignored) as JSON and Markdown. They record the git commit,
model, settings and dataset fingerprint. A report from a fake client is marked
`is_real_run: false` and starts with `NOT A REAL RESULT`; `compare` refuses it. In CI,
the live eval is a manual workflow (`.github/workflows/live-eval.yml`) that uploads the
reports as artifacts.

Metrics: exact-span extraction P/R/F1, joint P/R/F1 (span + label), recall on
contradicted claims, failure rate by type, consistency across repeats, p50/p95 latency,
tokens and cost.

## Layout

```
src/auditor/
  config.py, enums.py, metrics.py, cli.py
  db/          SQLAlchemy models, sessions
  catalogue/   strict CSV loader, in-memory and SQL catalogues
  llm/         provider-neutral types, Gemini/OpenAI/Groq clients, retries, ScriptedClient
  agent/       tools, validator, prompts, verify_answer loop
  audit/       run config, mentions, pipeline, worker
  api/         FastAPI app, routes, services, auth
  evals/       dataset, scoring, runner, compare
migrations/    Alembic
data/demo/     fictional catalogue, prompts, eval set
tests/         pytest; no test calls a real model API
frontend/      React web UI (services, Redux slices, routes, pages, components)
```

Deployment: `Dockerfile` (one image for API and worker), `docker-compose.yml`,
`fly.toml` (release command runs migrations), `.github/workflows/`.

## Known limitations

- **No live results yet.** Every score so far comes from fake clients in tests.
- **Small, synthetic eval set.** 16 fictional answers show the pipeline works; they do not
  measure real-world accuracy. Real answers labelled by two people would be the next step.
- **Groq's OpenAI compatibility is partial.** Some Groq models handle forced tool calls
  poorly; choose a Groq verifier model only after a live eval (`auditor eval`) with it.
- **One price setting.** Token prices are global, so cost is only right when a run's
  answer and verifier models share prices.
- **API models, not consumer apps.** Results describe a model through its API; ChatGPT or
  Gemini apps add search and system prompts and may answer differently.
- **Brand mentions are whole-word matches** of names and aliases; misspellings are missed.
- **Strict quote matching.** A model that changes one character in a quote fails
  validation; that is deliberate, but it costs a repair turn.
- **One shared catalogue** for all clients; the facts are only as good as the catalogue.
- **The PostgreSQL-only tests** (SKIP LOCKED, migrations on Postgres) run in CI, not in
  the default local test run.
- **The worker is a polling loop** on the database. Fine for this scale; a large deployment
  would want a proper queue.
