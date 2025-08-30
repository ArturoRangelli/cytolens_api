"""
Copyright (c) 2025 Binary Core LLC. All rights reserved.

This file is part of CytoLens, a proprietary product of Binary Core LLC.
Unauthorized copying, modification, or distribution of this file,
via any medium, is strictly prohibited.

JWT utilities for token creation and validation
"""

import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Cookie, HTTPException
from jose import jwt

from core import config


def create_access_token(identity: str) -> str:
    """
    Create a short-lived JWT access token.

    Access tokens are used for API requests and expire quickly (15 minutes).
    They contain minimal claims for performance.
    """
    now = datetime.utcnow()

    # Short expiration for access tokens
    expire = now + timedelta(minutes=config.settings.jwt_access_token_expire_minutes)

    to_encode = {
        "sub": identity,
        "exp": expire,
        "iat": now.timestamp(),
        "type": "access",
    }

    encoded_jwt = jwt.encode(
        to_encode,
        config.settings.jwt_secret_key,
        algorithm=config.settings.jwt_algorithm,
    )
    return encoded_jwt


def create_refresh_token(identity: str) -> str:
    """
    Create a refresh token with sliding expiration window.

    Refresh tokens expire after 30 minutes of inactivity.
    Each refresh resets the inactivity timer - users can stay logged in
    indefinitely as long as they're active (like banking apps).
    """
    now = datetime.utcnow()

    # Refresh token expires after inactivity period
    # Gets renewed with each refresh, so active users never get logged out
    expire = now + timedelta(minutes=config.settings.jwt_refresh_token_expire_minutes)

    # Generate unique token ID for revocation support
    token_id = secrets.token_urlsafe(32)

    to_encode = {
        "sub": identity,
        "exp": expire,  # Sliding window - resets on each refresh
        "iat": now.timestamp(),
        "jti": token_id,  # JWT ID for revocation
        "type": "refresh",
    }

    encoded_jwt = jwt.encode(
        to_encode,
        config.settings.jwt_secret_key,
        algorithm=config.settings.jwt_algorithm,
    )
    return encoded_jwt


def decode_token(token: str) -> dict:
    """
    Decode and validate a JWT token.
    """
    return jwt.decode(
        token,
        config.settings.jwt_secret_key,
        algorithms=[config.settings.jwt_algorithm],
    )


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
