FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS install
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY app ./app
RUN uv sync --frozen --no-dev

FROM python:3.12-slim
WORKDIR /app
COPY --from=install /app/.venv /app/.venv
COPY app ./app
ENV PATH="/app/.venv/bin:$PATH"
