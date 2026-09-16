# Multi-stage build: the builder installs dependencies (needs pip + any transient build
# artifacts), the final image only gets the installed packages and the app itself - no pip,
# no build cache, no test-only dependencies (those live in requirements-dev.txt, never
# installed here). Measured with an isolated `pip install --target` (i.e. what a fresh
# container actually gets, not skewed by anything already present on a dev machine):
# ~112MB of production dependencies + ~130-150MB python:3.12-slim base + a few MB of app
# code = roughly 260MB total, comfortably under the 500MB target.
FROM python:3.12-slim AS builder
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --prefix=/install -r requirements.txt

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY --from=builder /install /usr/local
COPY . .

RUN useradd -m appuser && mkdir -p /data/resumes && chown -R appuser /data /app
USER appuser

# Shell form so ${PORT} expands: Render (and similar PaaS hosts) inject PORT at runtime;
# falls back to 8000 for docker-compose / local use where PORT isn't set.
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers
