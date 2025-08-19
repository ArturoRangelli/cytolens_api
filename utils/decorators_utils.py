import hashlib
from functools import wraps

from flask import g, request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from flask_jwt_extended.exceptions import CSRFError, NoAuthorizationError
from werkzeug.exceptions import Unauthorized

from utils import postgres_utils


def require_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        # Check for API key in Authorization header first
        auth_header = request.headers.get("Authorization", "")

        if auth_header.startswith("Bearer "):
            raw_key = auth_header.replace("Bearer ", "").strip()
            hashed_key = hashlib.sha256(raw_key.encode()).hexdigest()
            user = postgres_utils.get_user_by_apikey(hashed_key=hashed_key)
            if user:
                g.current_user = user
                return fn(*args, **kwargs)

        # Try JWT + CSRF-based authentication
        try:
            verify_jwt_in_request()
            identity = get_jwt_identity()

            if identity:
                user = postgres_utils.get_user_by_username(username=identity)
                if user:
                    g.current_user = user
                    return fn(*args, **kwargs)

        except (NoAuthorizationError, CSRFError):
            pass

        # No auth method worked
        raise Unauthorized("Authentication required")

    return wrapper
