FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

RUN --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

FROM python:3.13-slim-bookworm

WORKDIR /app

COPY --from=builder --chown=app:app /app /app
COPY --chmod=0755 immich_smart_albums.py /app

ENV PATH="/app/.venv/bin:$PATH"

CMD ["./immich_smart_albums.py"]
