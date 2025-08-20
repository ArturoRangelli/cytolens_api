import hashlib
import secrets
from typing import Optional, Tuple

from utils import jwt_utils, password_utils, postgres_utils


async def register_user(username: str, password: str) -> None:
    """
    Handles user registration.
    """
    if postgres_utils.get_user_by_username(username=username):
        raise ValueError("Username already exists")

    hashed_pw = password_utils.get_password_hash(password=password)
    postgres_utils.set_user(username=username, password_hash=hashed_pw)


async def login_user(username: str, password: str) -> Tuple[str, str]:
    """
    Validate credentials and return access token and CSRF token for cookies.
    Raises ValueError on invalid credentials.
    """
    user = postgres_utils.get_user_by_username(username=username)
    if not user or not password_utils.verify_password(
        plain_password=password, hashed_password=user["password_hash"]
    ):
        raise ValueError("Invalid credentials")

    access_token = jwt_utils.create_access_token(identity=username)
    csrf_token = jwt_utils.get_csrf_token(access_token=access_token)

    return access_token, csrf_token


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

    return raw_key
