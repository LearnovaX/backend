# ============================================================================
# Stage 0 — uv binary (pinned immutable artifact)
# ============================================================================

FROM ghcr.io/astral-sh/uv@sha256:1025398289b62de8269e70c45b91ffa37c373f38118d7da036fb8bb8efc85d97 AS uv
# uv version: 0.11.14

# ============================================================================
# Stage 1 — Builder
# ============================================================================

FROM python:3.14-slim-bookworm AS builder

# Python + uv behavior
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /build

# System dependencies required for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    libssl-dev \
    ca-certificates \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr-rus \
    tesseract-ocr-uzb \
    && rm -rf /var/lib/apt/lists/*

# Copy pinned uv binary
COPY --from=uv /uv /usr/local/bin/uv

# Copy dependency manifests first for maximum layer caching
COPY pyproject.toml uv.lock ./

# Create isolated virtual environment
RUN uv venv /opt/venv

# Export locked dependencies and install into venv
RUN uv export \
        --locked \
        --no-dev \
        --format requirements-txt \
        > requirements.txt \
    && . /opt/venv/bin/activate \
    && uv pip install \
        --no-cache \
        -r requirements.txt

# ============================================================================
# Stage 2 — Runtime
# ============================================================================

FROM python:3.14-slim-bookworm AS runtime

# Runtime environment
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Runtime-only packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    dumb-init \
    ca-certificates \
    curl \
    tesseract-ocr \
    tesseract-ocr-rus \
    tesseract-ocr-uzb \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd --gid 10001 appuser && \
    useradd \
        --uid 10001 \
        --gid appuser \
        --create-home \
        --shell /usr/sbin/nologin \
        appuser

# Copy prebuilt virtual environment
COPY --from=builder /opt/venv /opt/venv

# Copy application source
COPY --chown=appuser:appuser . .

# Pre-create runtime directories so empty folders exist in the image and are writable
# Update this line in your Dockerfile
RUN mkdir -p /app/logs /app/staticfiles /app/media /app/static && \
    chown -R appuser:appuser /app/logs /app/staticfiles /app/media /app/static && \
    chmod -R ug+rwX /app/logs /app/staticfiles /app/media /app/static


# Ensure entrypoint is executable
RUN chmod +x /app/entrypoint.sh

# Drop privileges
USER appuser

# Proper PID 1 behavior
ENTRYPOINT ["/usr/bin/dumb-init", "--"]

# Start application
CMD ["/app/entrypoint.sh"]
