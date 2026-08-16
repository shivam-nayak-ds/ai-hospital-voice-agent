import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.routes.auth import router as auth_router
from api.routes.chat import router as chat_router
from api.routes.health import router as health_router
from api.routes.livekit_voice import router as livekit_router
from api.routes.panel import router as panel_router
from api.routes.twilio_voice import router as twilio_router
from config.settings import settings
from src.core.handlers import register_exception_handlers
from src.core.middleware.rate_limit import RedisRateLimitMiddleware
from src.core.middleware.security_headers import SecurityHeadersMiddleware
from src.utils.logger import custom_logger as logger

# Initialize FastAPI App
app = FastAPI(
    title=settings.APP_NAME,
    description="ASHA AI Hospital Voice Agent API backend.",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Bind CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Bind Redis Rate Limiter Middleware (30 req/min per IP)
app.add_middleware(RedisRateLimitMiddleware, limit=30, window=60)

# Bind Security Headers Middleware (OWASP-compliant headers on all responses)
app.add_middleware(SecurityHeadersMiddleware)


# Register Global Exception Handlers
register_exception_handlers(app)

# Include Routers
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(twilio_router)
app.include_router(livekit_router)
app.include_router(panel_router)

# Mount static files for browser UI (LiveKit demo, etc.)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", summary="Root Welcome Endpoint")
async def root():
    """Welcome endpoint for ASHA Voice AI server."""
    return {
        "status": "online",
        "message": f"Welcome to the {settings.APP_NAME} API Service.",
        "panel": "/panel",
        "documentation": "/docs"
    }


@app.get("/panel", include_in_schema=False)
async def serve_panel():
    """Serve the hospital admin panel HTML."""
    return FileResponse("static/index.html")

# Startup and Shutdown Lifecycle Logs
@app.on_event("startup")
async def startup_event():
    logger.success("ASHA AI Hospital Agent Server has started successfully.")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("ASHA AI Hospital Agent Server is shutting down gracefully.")


if __name__ == "__main__":
    logger.info(f"Running locally in {settings.APP_ENV} mode...")
    uvicorn.run("api.main:app", host="127.0.0.1", port=8000, reload=True)
