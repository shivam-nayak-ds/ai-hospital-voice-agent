import time

import redis.asyncio as aioredis
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from config.settings import settings
from src.utils.logger import custom_logger as logger


class RedisRateLimitMiddleware(BaseHTTPMiddleware):
    """
    Production-grade Redis Sliding Window Rate Limiter Middleware.
    Prevents DDoS, brute-forcing, and API abuse by limiting requests per IP.
    """
    def __init__(self, app, limit: int = 30, window: int = 60):
        super().__init__(app)
        self.limit = limit
        self.window = window
        self.redis_client = None

    async def _get_redis(self, request: Request) -> aioredis.Redis:
        # Check if the app lifecycle has a cached Redis client
        if hasattr(request.app.state, "redis_client"):
            return request.app.state.redis_client
            
        if not self.redis_client:
            self.redis_client = aioredis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD,
                decode_responses=True
            )
            request.app.state.redis_client = self.redis_client
        return self.redis_client

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip rate limiting for static documentation, root, and health checks
        path = request.url.path
        if path in ["/", "/docs", "/redoc", "/openapi.json", "/health", "/health/ready"]:
            return await call_next(request)

        try:
            r = await self._get_redis(request)
            
            # Track callers by unique client IP and request route path
            client_ip = request.client.host if request.client else "unknown_ip"
            key = f"rate_limit:{client_ip}:{path}"
            
            current_time = time.time()
            old_time = current_time - self.window
            
            # Execute commands inside an atomic Redis pipeline
            async with r.pipeline(transaction=True) as pipe:
                pipe.zremrangebyscore(key, 0, old_time)
                pipe.zadd(key, {str(current_time): current_time})
                pipe.zcard(key)
                pipe.expire(key, self.window)
                
                _, _, count, _ = await pipe.execute()
                
            if count > self.limit:
                logger.warning(f"Rate limit reached for IP {client_ip} on path {path} ({count}/{self.limit} reqs)")
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "success": False,
                        "error_code": "RATE_LIMIT_EXCEEDED",
                        "message": f"Rate limit exceeded. Maximum of {self.limit} requests per {self.window} seconds."
                    }
                )
                
        except Exception as e:
            # Resiliency: Fail open in case of Redis connection drops to ensure service availability
            logger.critical(f"Redis Rate Limiting unavailable, failing open: {e}")
            
        return await call_next(request)
