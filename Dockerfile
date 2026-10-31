# One image for both the API and the worker; the command decides which one runs.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install the package first (this layer is rebuilt only when the code changes).
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install .

# Migrations and the demo data are needed at runtime (alembic, `auditor seed`).
COPY alembic.ini ./
COPY migrations ./migrations
COPY data ./data

# Never run as root: a bug in the app should not own the container.
RUN useradd --create-home --uid 10001 auditor
USER auditor

EXPOSE 8000

# Checks the API. The worker serves no HTTP, so docker-compose turns this off for it.
# Plain Python, so the slim image needs no curl.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD ["python", "-c", "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=4).status == 200 else 1)"]

CMD ["uvicorn", "auditor.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
