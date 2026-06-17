"""Global error handling — safe responses, no internal details exposed."""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Base application error with user-safe message."""
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class AuthError(AppError):
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, status_code=401)


class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404)


class ValidationError(AppError):
    def __init__(self, message: str = "Invalid input"):
        super().__init__(message, status_code=422)


def register_error_handlers(app: FastAPI):
    """Register global exception handlers."""

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": True, "message": exc.message},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        """Catch Pydantic validation errors and return user-friendly messages."""
        errors = exc.errors()
        if errors:
            # Get the first error's message
            first = errors[0]
            msg = first.get("msg", "Invalid input")
            # Strip "Value error, " prefix that Pydantic adds
            if msg.startswith("Value error, "):
                msg = msg[len("Value error, "):]
        else:
            msg = "Invalid input"

        return JSONResponse(
            status_code=422,
            content={"error": True, "message": msg},
        )

    @app.exception_handler(Exception)
    async def general_error_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled error: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": True, "message": "Something went wrong. Please try again."},
        )
