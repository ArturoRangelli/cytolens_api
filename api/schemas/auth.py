from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator


class RegisterRequest(BaseModel):
    username: str
    password: str

    @field_validator("username")
    def validate_username(cls, value):
        if len(value) < 3:
            raise ValueError("Username must be at least 3 characters long.")
        return value

    @field_validator("password")
    def validate_password(cls, value):
        if len(value) < 6:
            raise ValueError("Password must be at least 6 characters long.")
        return value


class RegisterResponse(BaseModel):
    message: str


class LoginRequest(BaseModel):
    username: str
    password: str

    @field_validator("username")
    def validate_username(cls, value):
        if not value.strip():
            raise ValueError("Username cannot be empty.")
        return value

    @field_validator("password")
    def validate_password(cls, value):
        if not value.strip():
            raise ValueError("Password cannot be empty.")
        return value


class LoginResponse(BaseModel):
    message: str


class LogoutResponse(BaseModel):
    message: str


class CreateApiKeyRequest(BaseModel):
    name: str = "default"
    expires_at: Optional[str] = None


class CreateApiKeyResponse(BaseModel):
    api_key: str
