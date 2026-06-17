# ─── Stage 1: Build Dependencies ──────────────────────────────────────────────
FROM python:3.10-slim AS builder

WORKDIR /build

# System dependencies for audio processing (PyAudio needs portaudio)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    portaudio19-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ─── Stage 2: Production Runtime ──────────────────────────────────────────────
FROM python:3.10-slim AS runtime

WORKDIR /app

# Minimal runtime system deps only (no build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    portaudio19-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder stage
COPY --from=builder /install /usr/local

# Copy application code
COPY . .

# Create non-root user for security (prevents container escape attacks)
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Health check: Docker auto-restarts unhealthy containers
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health/ready || exit 1

# Production: Gunicorn with Uvicorn workers (handles 4 concurrent workers)
# --workers 4: 4 worker processes (adjust to 2*CPU+1 in production)
# --worker-class uvicorn.workers.UvicornWorker: ASGI support for FastAPI
# --timeout 120: LLM calls can take up to 7s + buffer
# --graceful-timeout 30: Allow in-flight requests to finish on shutdown
CMD ["gunicorn", "api.main:app", \
     "--workers", "4", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "120", \
     "--graceful-timeout", "30", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]

