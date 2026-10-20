FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.12.9 /uv /uvx /bin/

WORKDIR /app

RUN apt-get update \
    && apt-get install --yes --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

RUN uv venv /opt/venv

ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY . .
RUN uv pip install --no-cache .

FROM python:3.12-slim AS runtime

WORKDIR /app

RUN useradd --create-home --uid 10001 appuser

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /app/app ./app
COPY --from=builder /app/core ./core
COPY --from=builder /app/adapters ./adapters
COPY --from=builder /app/providers ./providers
COPY --from=builder /app/data ./data

ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

USER appuser

CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port \"${PORT:-8080}\""]
