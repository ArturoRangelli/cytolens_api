"""
API exception handlers
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from jose import JWTError
from pydantic import ValidationError


async def validation_exception_handler(request: Request, exc: ValidationError):
    """Handle Pydantic validation errors"""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()}
    )


async def jwt_exception_handler(request: Request, exc: JWTError):
    """Handle JWT token errors"""
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": "Invalid or expired token"}
    )


async def value_error_handler(request: Request, exc: ValueError):
    """Handle ValueError from services (e.g., invalid credentials, duplicate users)"""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)}
    )


async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors"""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred"}
    )