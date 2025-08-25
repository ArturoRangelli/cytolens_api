"""
Copyright (c) 2025 Binary Core LLC. All rights reserved.

This file is part of CytoLens, a proprietary product of Binary Core LLC.
Unauthorized copying, modification, or distribution of this file,
via any medium, is strictly prohibited.

API exception handlers for global error handling
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from jose import JWTError
from pydantic import ValidationError

from utils import logging_utils

logger = logging_utils.get_logger("cytolens.api.exceptions")


async def validation_exception_handler(request: Request, exc: ValidationError):
    """Handle Pydantic validation errors"""
    logger.warning(f"Validation error at {request.method} {request.url.path}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()},
    )


async def jwt_exception_handler(request: Request, exc: JWTError):
    """Handle JWT token errors"""
    logger.warning(
        f"JWT auth failed at {request.method} {request.url.path} from {request.client.host}"
    )
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": "Invalid or expired token"},
    )


async def value_error_handler(request: Request, exc: ValueError):
    """Handle ValueError from services (e.g., invalid credentials, duplicate users)"""
    logger.warning(f"Client error at {request.method} {request.url.path}: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST, content={"detail": str(exc)}
    )


async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors"""
    logger.error(
        f"Server error at {request.method} {request.url.path}: {str(exc)}",
        exc_info=True,  # This logs the full stack trace
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred"},
    )
