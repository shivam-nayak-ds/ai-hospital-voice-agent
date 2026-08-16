"""
health.py
---------
Production-grade health check and readiness probe endpoints.
Used by Docker HEALTHCHECK, Kubernetes liveness/readiness probes,
and uptime monitoring tools (UptimeRobot, Datadog, Grafana).

Endpoints:
  GET /health  → Liveness check: Is the process alive?
  GET /ready   → Readiness check: Is the app ready to serve traffic?
"""

import time

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/health", tags=["Health"])

# Track server start time for uptime reporting
_start_time = time.time()


@router.get("", summary="Liveness Probe")
async def health_check():
    """
    Liveness check — confirms the process is alive and event loop is responsive.
    Docker HEALTHCHECK and Kubernetes liveness probe should call this.

    Returns 200 if alive, used to auto-restart crashed containers.
    """
    uptime_seconds = round(time.time() - _start_time, 1)

    # Check individual service connectivity
    db_status = await _check_database()
    redis_status = await _check_redis()
    qdrant_status = await _check_qdrant()

    all_healthy = all([
        db_status["status"] == "ok",
        redis_status["status"] == "ok",
        qdrant_status["status"] == "ok",
    ])

    payload = {
        "status": "healthy" if all_healthy else "degraded",
        "uptime_seconds": uptime_seconds,
        "services": {
            "database": db_status,
            "redis": redis_status,
            "qdrant": qdrant_status,
        }
    }

    status_code = 200 if all_healthy else 503
    return JSONResponse(content=payload, status_code=status_code)


@router.get("/ready", summary="Readiness Probe")
async def readiness_check():
    """
    Readiness check — confirms the app is fully initialized and ready to serve.
    Kubernetes readiness probe calls this before routing traffic to a pod.

    Returns 200 if ready, 503 if still warming up (e.g., models loading).
    """
    return JSONResponse(
        content={
            "status": "ready",
            "message": "Asha AI Hospital Agent is ready to serve requests."
        },
        status_code=200
    )


# ─── Private Service Check Helpers ────────────────────────────────────────────

async def _check_database() -> dict:
    """Pings the PostgreSQL database with a lightweight SELECT 1 query."""
    try:
        from sqlalchemy import text

        from src.db.session import engine
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ok", "latency_ms": None}
    except Exception as e:
        return {"status": "error", "detail": str(e)[:120]}


async def _check_redis() -> dict:
    """Sends a PING command to Redis and expects PONG."""
    try:
        import redis.asyncio as aioredis

        from config.settings import settings
        r = aioredis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            socket_connect_timeout=2
        )
        pong = await r.ping()
        await r.aclose()
        return {"status": "ok" if pong else "error"}
    except Exception as e:
        return {"status": "error", "detail": str(e)[:120]}


async def _check_qdrant() -> dict:
    """Checks if the Qdrant vector DB is reachable via its HTTP API."""
    try:
        import httpx

        from config.settings import settings
        url = f"http://{settings.QDRANT_HOST}:{settings.QDRANT_PORT}/healthz"
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(url)
        return {"status": "ok" if resp.status_code == 200 else "error"}
    except Exception as e:
        return {"status": "error", "detail": str(e)[:120]}
