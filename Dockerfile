# Stage 1: Build virtualenv using official Astral uv
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv

WORKDIR /app

# Install dependencies first for layer caching
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# Copy source and build
COPY . .
RUN uv sync --frozen --no-dev

# Stage 2: Minimal Runtime Image
FROM python:3.12-slim

WORKDIR /app

# Copy virtualenv and application code
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src
COPY --from=builder /app/pyproject.toml /app/pyproject.toml

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app/src" \
    PYTHONUNBUFFERED=1

EXPOSE 8080

CMD ["uvicorn", "titip_makan.main:app", "--host", "0.0.0.0", "--port", "8080"]
