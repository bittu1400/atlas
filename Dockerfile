# Runtime image for the Atlas API and worker.
#
# `docker-compose.yml` has named this file since the Compose file was written;
# it did not exist, so `docker compose up` failed on the first build (defect
# V-05). ffmpeg is installed because `StubRenderer` shells out to it, which is
# the only system dependency Atlas has outside the Python toolchain.

FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:/root/.local/bin:${PATH}"

RUN apt-get update \
    && apt-get install --no-install-recommends -y ffmpeg curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Dependency layer first, so a source edit does not reinstall the world.
COPY pyproject.toml uv.lock README.md ./
COPY packages/atlas/src/atlas/__init__.py packages/atlas/src/atlas/__init__.py
RUN uv sync --frozen --no-install-project

COPY . .
RUN uv sync --frozen

# Blob and snapshot roots are bind-mounted by Compose; create them so a bare
# `docker run` still starts.
RUN mkdir -p /var/atlas/blobs /var/atlas/snapshots

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
