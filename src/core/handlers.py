from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.core.domain_exceptions import AshaBaseException
from src.core.logger import custom_logger as logger


async def asha_exception_handler(request: Request, exc: AshaBaseException):
    request_id = getattr(request.state, "request_id", "unknown")
    logger.bind(request_id=request_id).warning(f"Domain error {exc.error_code} ({exc.status_code}): {exc.message}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error_code": exc.error_code,
            "message": exc.message,
            "request_id": request_id
        }
    )

async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    request_id = getattr(request.state, "request_id", "unknown")
    logger.bind(request_id=request_id).warning(f"HTTP error {exc.status_code}: {exc.detail}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error_code": f"HTTP_{exc.status_code}",
            "message": exc.detail,
            "request_id": request_id
        }
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    request_id = getattr(request.state, "request_id", "unknown")
    logger.bind(request_id=request_id).error(f"Input validation failure: {exc.errors()}")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error_code": "VALIDATION_ERROR",
            "message": "Input validation checks failed.",
            "request_id": request_id
        }
    )

async def unexpected_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "unknown")
    logger.bind(request_id=request_id).exception(f"Unhandled critical exception: {exc}")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error_code": "INTERNAL_SERVER_ERROR",
            "message": "An unhandled exception occurred. Support team has been notified.",
            "request_id": request_id
        }
    )


def register_exception_handlers(app):
    """Binds standard global exception decorators to the FastAPI application instance."""
    app.add_exception_handler(AshaBaseException, asha_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unexpected_exception_handler)

