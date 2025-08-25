"""
Copyright (c) 2025 Binary Core LLC. All rights reserved.

This file is part of CytoLens, a proprietary product of Binary Core LLC.
Unauthorized copying, modification, or distribution of this file,
via any medium, is strictly prohibited.

Security dependencies for protecting API endpoints
"""
import hashlib
from typing import Annotated, Dict, Optional

from fastapi import Cookie, Depends, Header, HTTPException
from jose import jwt

from core import config
from utils import postgres_utils


async def verify_user_access(
    authorization: Annotated[Optional[str], Header()] = None,
    access_token: Annotated[Optional[str], Cookie()] = None,
) -> Dict:
    """
    Verify user access via API key or JWT token.
    
    Authentication priority:
    1. API key from Authorization header (Bearer token)
    2. JWT from cookie (web session)
    
    Returns:
        User dictionary if authenticated
        
    Raises:
        HTTPException 401 if authentication fails
    """
    
    # Check API key authentication
    if authorization and authorization.startswith("Bearer "):
        raw_key = authorization.replace("Bearer ", "").strip()
        hashed_key = hashlib.sha256(raw_key.encode()).hexdigest()
        user = postgres_utils.get_user_by_apikey(hashed_key=hashed_key)
        if user:
            return user
    
    # Check JWT authentication
    if access_token:
        try:
            payload = jwt.decode(
                access_token,
                config.settings.jwt_secret_key,
                algorithms=[config.settings.jwt_algorithm],
            )
            username = payload.get("sub")
            if username:
                user = postgres_utils.get_user_by_username(username=username)
                if user:
                    return user
        except Exception:
            # JWT validation failed, continue to check other methods
            pass
    
    # Authentication failed
    raise HTTPException(
        status_code=401,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )


# Type alias for cleaner usage in routes
CurrentUser = Annotated[Dict, Depends(verify_user_access)]