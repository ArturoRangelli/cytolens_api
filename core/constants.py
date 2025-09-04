"""
Copyright (c) 2025 Binary Core LLC. All rights reserved.

This file is part of CytoLens, a proprietary product of Binary Core LLC.
Unauthorized copying, modification, or distribution of this file,
via any medium, is strictly prohibited.

Application constants for the CytoLens API
"""


# Task states from Celery (inference service)
class TaskState:
    PENDING = "PENDING"
    STARTED = "STARTED"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    REVOKED = "REVOKED"

    # Terminal states (cannot be changed)
    TERMINAL = [SUCCESS, FAILURE, REVOKED]

    # All valid states
    ALL = [PENDING, STARTED, SUCCESS, FAILURE, REVOKED]


# Error messages
class ErrorMessage:
    INVALID_STATE = "Invalid state"
    INVALID_TASK_ID = "Invalid task ID"
    RESOURCE_NOT_FOUND = "Resource not found"
    UNAUTHORIZED = "Unauthorized"
    UPDATE_FAILED = "Update failed"


# Authentication error messages
class AuthErrorMessage:
    USERNAME_EXISTS = "Username already exists"
    INVALID_CREDENTIALS = "Invalid credentials"
    REFRESH_TOKEN_REQUIRED = "Refresh token required"
    INVALID_TOKEN_TYPE = "Invalid token type"
    INVALID_TOKEN = "Invalid token"
    USER_NOT_FOUND = "User no longer exists"
    INVALID_SESSION = "Invalid session"
    API_KEY_EXISTS = "API key with name '{}' already exists for this user"


# Task messages
class TaskMessage:
    QUEUED = "Inference task queued"
    CANCELLED = "Inference task cancelled"
    ALREADY_TERMINAL = "Task already {}"  # Format with state.lower()
    STATUS_UPDATED = "Task status updated"


# Default values
class Defaults:
    CONFIDENCE = 0.5
    TASK_LIMIT = 20
    TASK_OFFSET = 0

    # HTTP client timeouts (in seconds)
    INFERENCE_REQUEST_TIMEOUT = 30.0
    CANCEL_REQUEST_TIMEOUT = 10.0
