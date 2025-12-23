# Builder stage
FROM python:3.13 AS builder

ENV PYTHONUNBUFFERED=1

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN apt-get update && apt-get install -y --no-install-recommends \
  # Base
  gettext \
  libpq5 \
  media-types \
  nodejs \
  unixodbc \
  # Builder
  build-essential \
  git \
  gzip \
  libpq-dev \
  libssl-dev \
  libyaml-dev \
  unixodbc-dev \
  zlib1g-dev \
  && apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

WORKDIR /app

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock ./
COPY clients ./clients

# Sync dependencies to /opt/venv (outside /app which gets volume-mounted in dev)
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV UV_LINK_MODE=copy
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --all-extras

VOLUME ["/data"]

# Runtime stage
FROM python:3.13-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONPATH="/app/rdrf/:${PYTHONPATH}"
ENV DJANGO_SETTINGS_MODULE=rdrf.settings
ENV STATIC_ROOT="/data/static"
ENV WRITABLE_DIRECTORY="/data/scratch"
ENV LOCALE_PATHS="/app/translations/locale"
ENV LOG_DIRECTORY="/data/log"
ENV MEDIA_ROOT="/data/static/media"

RUN apt-get update && apt-get install -y --no-install-recommends \
  # Base
  gettext \
  libpq5 \
  media-types \
  nodejs \
  postgresql-client \
  unixodbc \
  unixodbc-dev \
  build-essential \
  libmagic1 \
  git \
  && apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Copy venv from builder to /opt/venv
COPY --from=builder /opt/venv /opt/venv

WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./
COPY clients ./clients

# Finalize dependency install
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV UV_LINK_MODE=copy
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --all-extras

# Add venv to PATH
ENV PATH="/opt/venv/bin:$PATH"

COPY docker/dev/docker-entrypoint.sh /
RUN chmod +x /docker-entrypoint.sh

COPY docker/dev/lambda/aws-lambda-rie /
RUN chmod +x /aws-lambda-rie

VOLUME ["/app", "/data"]

ENV HOME=/data
WORKDIR /data

EXPOSE 8000

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["runserver_plus"]
