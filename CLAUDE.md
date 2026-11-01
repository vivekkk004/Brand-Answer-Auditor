# CLAUDE.md

Project: **Brand Answer Auditor**. It measures how often AI assistants name brands
(inclusion, with Wilson confidence intervals) and checks product claims in their answers
against a fact catalogue (accuracy). Full behaviour is in `SPEC.md`.

This is a portfolio project for an AI Software Engineer interview. The owner must be able
to explain every line, so keep changes small and explain decisions in simple English.

## Working rules

1. **Spec first.** Code must match `SPEC.md`. If behaviour changes, update `SPEC.md` in
   the same commit. If the spec is unclear, ask; do not guess.
2. **One phase at a time.** At the end of each phase:
   1. Run `ruff check .`, `ruff format --check .` and `pytest`. (Web UI changes are
      checked and committed in the frontend repository; see its CLAUDE.md.)
   2. Show the real output of all three.
   3. Summarise what changed and why, in simple English.
   4. Commit with a clear message.
   5. **Stop and wait** for the owner before starting the next phase.
3. **Tests never call real model APIs.** Use a scripted fake client that returns
   pre-written responses (and pre-written errors) in order.
4. **Never invent metrics, results or scores. Never hardcode eval numbers.** Numbers in
   reports and the README come only from running the code. Expected values in unit tests
   of pure functions (for example a Wilson interval worked out from the formula) are fine.
5. **Check the installed SDK before writing SDK code.** Look up the installed versions of
   `google-genai` and `openai` and read the real signatures (for example with
   `pip show <package>` and `python -c "import inspect, ...; print(inspect.signature(...))"`).
   Do not rely on memory. Mention the versions checked in the phase summary.
6. **No secrets in code, logs or tests.** All config comes from environment variables
   (pydantic-settings). Tests use obviously fake values like `test-key`.
7. **Prefer simple, explicit code over frameworks.** Plain functions and classes, type
   hints, small modules. No clever metaprogramming. Comments explain *why*, not *what*.

## Stack

Python 3.12, FastAPI, Pydantic v2, pydantic-settings, SQLAlchemy 2, Alembic,
PostgreSQL 16 (SQLite only for fast tests), `google-genai`, `openai`, pytest, ruff,
Docker, GitHub Actions, Fly.io.

Web UI: a separate repository, https://github.com/vivekkk004/Brand-Answer-Auditor-frontend (React 19, Redux
Toolkit, Vite). Locally it is cloned into `frontend/`, which this repo ignores; its own
CLAUDE.md holds the UI rules, stack and commands.

**Not allowed without the owner's approval:** LangGraph, any vector database, Celery,
Redis. **Ask before adding any other dependency**, including dev tools.

## Testing

- Default test run uses SQLite so it is fast. CI also runs migrations (and the test
  suite) against a PostgreSQL 16 service.
- Model clients are passed in (dependency injection), so tests can swap in the fake client.
- Sleep and clock functions used by retries are injectable, so tests do not wait.
- Every acceptance criterion in `SPEC.md` section 8 should end up with at least one test.

## Commands

Setup (Windows; the project targets Python 3.12):

```
"C:\Program Files\Python312\python.exe" -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
```

Every phase ends with:

```
ruff check .
ruff format --check .
pytest
```

Other commands:

```
auditor check-data          # catalogue, prompts and eval set are consistent (no DB needed)
auditor seed                # load data/demo CSVs into DATABASE_URL
auditor worker              # process queued audit runs until SIGTERM / Ctrl+C
auditor create-api-key NAME # create an API client; prints its key once
auditor worker --once       # process one queued run, then exit
auditor eval --split dev --repeats 3   # LIVE: calls the real verifier model; costs money
auditor compare BASE.json NEW.json --max-drop 0.02   # exit 1 on a regression
uvicorn auditor.api.app:create_app --factory   # run the API
alembic upgrade head        # apply migrations to DATABASE_URL
alembic revision --autogenerate -m "..."   # after changing db/models.py
```

PostgreSQL tests (migrations, SKIP LOCKED, full pipeline) run only when `TEST_POSTGRES_URL`
points at an empty database.

## Layout

- `src/auditor/` — the package (`config.py`, `enums.py`, `db/`, `catalogue/`, `cli.py`)
- `src/auditor/llm/` — provider-neutral model layer: `types.py`, `errors.py`, `retry.py`,
  `openai_client.py`, `gemini_client.py`, `groq_client.py` (OpenAI client on Groq's endpoint),
  `factory.py`, and `fake.py` (`ScriptedClient` for tests)
- `src/auditor/agent/` — the verification agent: `schemas.py`, `tools.py` (JSON schemas +
  `ToolExecutor`), `validator.py` (quote → offsets, all issues at once), `prompts.py` (v1, v2),
  `verifier.py` (`verify_answer` loop), `fallback.py` (optional second verifier)
- `src/auditor/audit/` — audit runs: `run_config.py`, `mentions.py`, `persistence.py`,
  `pipeline.py` (claim, collect, verify, metrics, budget), `worker.py`
- `src/auditor/metrics.py` — Wilson interval, P/R/F1, percentile, cost
- `src/auditor/evals/` — `dataset.py` (strict loading, gold offsets, fingerprint),
  `scoring.py` (exact-span P/R/F1), `runner.py` (`run_eval`, reports, `compare_reports`)
- `reports/` — eval output, git-ignored; never commit result numbers
- `src/auditor/api/` — FastAPI: `app.py` (`create_app`), `routes.py` (thin handlers),
  `services.py` (business logic), `deps.py`, `security.py`, `schemas.py`, `errors.py`
- `migrations/` — Alembic; `migrations/versions/` is autogenerated and excluded from ruff
- `data/demo/` — fictional catalogue, prompts and eval set
- `frontend/` — not part of this repo: a local clone of the web UI repository (ignored)
- `tests/` — pytest; no test calls a real model API
- `Dockerfile` (one image: API by default, `auditor worker` for the worker), `docker-compose.yml`,
  `fly.toml`, `.github/workflows/ci.yml`, `.github/workflows/live-eval.yml` (manual, paid)

## Commits

- One commit per phase (more only if the owner asks).
- Message: short imperative summary line, then a few lines on what and why.
- Never commit `.env` files, API keys or generated eval reports that contain secrets.
