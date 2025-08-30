"""
Copyright (c) 2025 Binary Core LLC. All rights reserved.

This file is part of CytoLens, a proprietary product of Binary Core LLC.
Unauthorized copying, modification, or distribution of this file,
via any medium, is strictly prohibited.

Authentication services for user registration, login, and API key management
"""

import hashlib
import secrets
from typing import Optional, Tuple

from utils import jwt_utils, logging_utils, password_utils, postgres_utils

logger = logging_utils.get_logger("cytolens.services.auth")


async def register_user(username: str, password: str) -> None:
    """
    Handles user registration.
    """
    if postgres_utils.get_user_by_username(username=username):
        raise ValueError("Username already exists")

    hashed_pw = password_utils.get_password_hash(password=password)
    user = postgres_utils.set_user(username=username, password_hash=hashed_pw)
    logger.info(f"User registered: {username} (ID: {user['id']})")


async def login_user(username: str, password: str) -> Tuple[str, str]:
    """
    Validate credentials and return access and refresh tokens.
    Raises ValueError on invalid credentials.
    """
    user = postgres_utils.get_user_by_username(username=username)
    if not user or not password_utils.verify_password(
        plain_password=password, hashed_password=user["password_hash"]
    ):
        logger.warning(f"Failed login attempt for username: {username}")
        raise ValueError("Invalid credentials")

    # Create both tokens for the session
    access_token = jwt_utils.create_access_token(identity=username)
    refresh_token = jwt_utils.create_refresh_token(identity=username)
    logger.info(f"User login: {username} (ID: {user['id']})")

    return access_token, refresh_token


async def refresh_tokens(refresh_token: str) -> Tuple[str, str, str]:
    """
    Validate refresh token and issue new token pair.

    Implements sliding window expiration - each refresh resets the 30-minute
    inactivity timer, allowing users to stay logged in indefinitely while active.
    """
    if not refresh_token:
        raise ValueError("Refresh token required")

    # Decode and validate refresh token - will raise if invalid
    payload = jwt_utils.decode_token(refresh_token)

    # Verify it's a refresh token
    if payload.get("type") != "refresh":
        raise ValueError("Invalid token type")

    username = payload.get("sub")
    if not username:
        raise ValueError("Invalid token")

    # Verify user still exists and is active
    user = postgres_utils.get_user_by_username(username=username)
    if not user:
        raise ValueError("User no longer exists")

    # Generate new token pair
    new_access_token = jwt_utils.create_access_token(identity=username)
    new_refresh_token = jwt_utils.create_refresh_token(identity=username)

    logger.info(f"Token refreshed for user: {username}")

    return new_access_token, new_refresh_token, username


async def logout_user(username: str) -> None:
    """
    Log user logout event.
    """
    user = postgres_utils.get_user_by_username(username=username)
    if user:
        logger.info(f"User logout: {username} (ID: {user['id']})")


async def create_api_key(
    username: str,
    name: str = "default",
    expires_at: Optional[str] = None,
) -> str:
    """
    Generates a new API key for the authenticated user and stores its hash.
    Returns the raw API key.
    """
    user = postgres_utils.get_user_by_username(username=username)

    if not user:
        raise ValueError("Invalid session")

    # Check if API key name already exists for this user
    if postgres_utils.get_apikey_by_name(user_id=user["id"], name=name):
        raise ValueError(f"API key with name '{name}' already exists for this user")

    raw_key = secrets.token_urlsafe(32)
    hashed_key = hashlib.sha256(raw_key.encode()).hexdigest()

    postgres_utils.set_apikey(
        user_id=user["id"],
        hashed_key=hashed_key,
        name=name,
        expires_at=expires_at,
    )

    logger.info(f"API key '{name}' created for user {username} (ID: {user['id']})")

    return raw_key
