"""
Copyright (c) 2025 Binary Core LLC. All rights reserved.

This file is part of CytoLens, a proprietary product of Binary Core LLC.
Unauthorized copying, modification, or distribution of this file,
via any medium, is strictly prohibited.

Authentication routes for user registration, login, and API key management
"""

from fastapi import APIRouter, Depends, Response

from api.schemas import auth as auth_schemas
from api.services import auth as auth_services
from utils import jwt_utils

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
    responses={404: {"description": "Not found"}},
)


@router.post("/register", response_model=auth_schemas.RegisterResponse, status_code=201)
async def register_endpoint(
    request: auth_schemas.RegisterRequest,
) -> auth_schemas.RegisterResponse:
    """
    Register a new user.
    Returns a success message upon successful registration.
    """
    await auth_services.register_user(
        username=request.username,
        password=request.password,
    )
    return auth_schemas.RegisterResponse(message="User registered successfully")


@router.post("/login", response_model=auth_schemas.LoginResponse)
async def login_endpoint(
    request: auth_schemas.LoginRequest,
    response: Response,
) -> auth_schemas.LoginResponse:
    """
    Login user and set authentication cookies.
    """
    access_token, csrf_token = await auth_services.login_user(
        username=request.username,
        password=request.password,
    )

    # Set access token cookie (httponly for security)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        secure=False,  # Set to True in production with HTTPS
    )

    # Set CSRF token cookie (not httponly so JS can read it)
    response.set_cookie(
        key="csrf_access_token",
        value=csrf_token,
        httponly=False,
        samesite="lax",
        secure=False,  # Set to True in production with HTTPS
    )

    return auth_schemas.LoginResponse(message="Login successful")


@router.post("/logout", response_model=auth_schemas.LogoutResponse)
async def logout_endpoint(
    response: Response,
    _: str = Depends(jwt_utils.get_current_user),  # Authentication check only
) -> auth_schemas.LogoutResponse:
    """
    Logout user and clear authentication cookies.
    Requires valid JWT token in cookie.
    """
    # Clear cookies by setting them with empty values and max_age=0
    response.set_cookie(
        key="access_token",
        value="",
        max_age=0,
        httponly=True,
        samesite="lax",
        secure=False,  # Set to True in production with HTTPS
    )

    response.set_cookie(
        key="csrf_access_token",
        value="",
        max_age=0,
        httponly=False,
        samesite="lax",
        secure=False,  # Set to True in production with HTTPS
    )

    return auth_schemas.LogoutResponse(message="Logout successful")


@router.post(
    "/api-keys", response_model=auth_schemas.CreateApiKeyResponse, status_code=201
)
async def create_api_key_endpoint(
    request: auth_schemas.CreateApiKeyRequest,
    current_user: str = Depends(jwt_utils.get_current_user),
) -> auth_schemas.CreateApiKeyResponse:
    """
    Create a new API key for the authenticated user.
    Requires valid JWT token in cookie.
    """
    api_key = await auth_services.create_api_key(
        username=current_user,
        name=request.name,
        expires_at=request.expires_at,
    )
    return auth_schemas.CreateApiKeyResponse(api_key=api_key)
