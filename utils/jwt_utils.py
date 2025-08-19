import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Cookie, HTTPException
from jose import jwt

from core import config


def create_access_token(identity: str) -> str:
    """Create a JWT access token with embedded CSRF token."""
    expires_delta = timedelta(minutes=config.settings.jwt_access_token_expire_minutes)
    expire = datetime.utcnow() + expires_delta
    csrf_token = secrets.token_urlsafe(32)
    to_encode = {
        "sub": identity,
        "exp": expire,
        "csrf": csrf_token,  # Embed CSRF token in the JWT
    }
    encoded_jwt = jwt.encode(
        to_encode,
        config.settings.jwt_secret_key,
        algorithm=config.settings.jwt_algorithm,
    )
    return encoded_jwt


def get_csrf_token(access_token: str) -> str:
    """Extract CSRF token from JWT access token."""
    payload = jwt.decode(
        access_token,
        config.settings.jwt_secret_key,
        algorithms=[config.settings.jwt_algorithm],
    )
    csrf_token = payload.get("csrf")
    if not csrf_token:
        raise ValueError("CSRF token not found in access token")
    return csrf_token


async def get_current_user(access_token: Optional[str] = Cookie(None)) -> str:
    """
    Dependency to validate JWT token from cookie and return current user.
    Used as a dependency for protected endpoints.
    """
    if not access_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = jwt.decode(
        access_token,
        config.settings.jwt_secret_key,
        algorithms=[config.settings.jwt_algorithm],
    )
    username: str = payload.get("sub")
    if username is None:
        raise HTTPException(
            status_code=401, detail="Invalid authentication credentials"
        )
    return username
