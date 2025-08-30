"""
Copyright (c) 2025 Binary Core LLC. All rights reserved.

This file is part of CytoLens, a proprietary product of Binary Core LLC.
Unauthorized copying, modification, or distribution of this file,
via any medium, is strictly prohibited.

Inference services for managing AI analysis tasks
"""

from typing import Any, Dict, List

import httpx

from core import config, constants
from utils import logging_utils, postgres_utils, sys_utils

logger = logging_utils.get_logger("cytolens.services.inference")


async def start_inference(
    slide_id: int, user_id: int, confidence: float = constants.Defaults.CONFIDENCE
) -> Dict[str, Any]:
    """
    Start inference for a slide by calling the inference service.
    The inference service will download the slide from S3 directly.
    """
    # Verify slide ownership
    slide_db = postgres_utils.get_slide_by_id(slide_id=slide_id, owner_id=user_id)
    if not slide_db:
        logger.warning(
            f"Unauthorized inference attempt for slide {slide_id} by user {user_id}"
        )
        raise ValueError(constants.ErrorMessage.RESOURCE_NOT_FOUND)

    # Prepare request matching the inference service schema
    payload = {
        "slide_id": str(slide_id),
        "file_extension": slide_db["type"],
        "confidence": confidence,
    }

    headers = {
        "X-API-Key": config.settings.inference_api_key,
        "Content-Type": "application/json",
    }

    # Call inference service
    logger.info(
        f"Starting inference for slide {slide_id} by user {user_id} (confidence: {confidence})"
    )

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{config.settings.inference_service_url}/inference",
            json=payload,
            headers=headers,
            timeout=constants.Defaults.INFERENCE_REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()

        # Create task in database
        task = postgres_utils.create_task(
            slide_id=slide_id,
            user_id=user_id,
            inference_task_id=data["inference_task_id"],
            state=data["state"],
            confidence=confidence,
            message=constants.TaskMessage.QUEUED,
        )

        logger.info(
            f"Inference task created: {task['id']} for slide {slide_id} by user {user_id}"
        )

        # Return in format expected by our schema
        return {
            "id": str(task["id"]),
            "state": data["state"],
            "message": constants.TaskMessage.QUEUED,
        }


async def get_tasks(
    user_id: int,
    state: str = None,
    limit: int = constants.Defaults.TASK_LIMIT,
    offset: int = constants.Defaults.TASK_OFFSET,
) -> List[Dict[str, Any]]:
    """
    Get all inference tasks for a user.
    """
    # Validate state if provided
    if state is not None and state not in constants.TaskState.ALL:
        raise ValueError(constants.ErrorMessage.INVALID_STATE)

    tasks = postgres_utils.get_tasks(
        user_id=user_id, state=state, limit=limit, offset=offset
    )

    logger.info(
        f"Tasks retrieved: {len(tasks)} tasks for user {user_id} (filter: {state or 'all'})"
    )

    # Format tasks for response
    return [
        {
            "id": str(task["id"]),
            "slide_id": str(task["slide_id"]),
            "state": task["state"],
            "message": task.get("message", ""),
            "confidence": task.get("confidence"),
            "created_at": task["created_at"],
            "completed_at": task.get("completed_at", ""),
        }
        for task in tasks
    ]


async def get_task_status(task_id: str, user_id: int) -> Dict[str, Any]:
    """
    Get the status of an inference task.
    """
    # Validate and convert task_id
    try:
        task_id_int = int(task_id)
    except (ValueError, TypeError):
        raise ValueError(constants.ErrorMessage.INVALID_TASK_ID)

    # Get task from database, ensuring user owns it
    task = postgres_utils.get_task_by_id(task_id=task_id_int, user_id=user_id)
    if not task:
        logger.warning(
            f"Unauthorized task status access attempt for task {task_id_int} by user {user_id}"
        )
        raise ValueError(constants.ErrorMessage.RESOURCE_NOT_FOUND)

    logger.info(
        f"Task status checked: {task_id_int} (state: {task['state']}) by user {user_id}"
    )

    # Return in format expected by our schema
    return {
        "id": str(task["id"]),
        "slide_id": str(task["slide_id"]),
        "state": task["state"],
        "message": task.get("message", ""),
        "confidence": task["confidence"],
        "created_at": task["created_at"],
        "completed_at": task.get("completed_at", ""),
    }


async def cancel_task(task_id: str, user_id: int) -> Dict[str, Any]:
    """
    Cancel an inference task.
    """
    # Validate and convert task_id
    try:
        task_id_int = int(task_id)
    except (ValueError, TypeError):
        raise ValueError(constants.ErrorMessage.INVALID_TASK_ID)

    # Verify task ownership
    task = postgres_utils.get_task_by_id(task_id=task_id_int, user_id=user_id)
    if not task:
        logger.warning(
            f"Unauthorized task cancel attempt for task {task_id_int} by user {user_id}"
        )
        raise ValueError(constants.ErrorMessage.RESOURCE_NOT_FOUND)

    # Check if task is already in terminal state to avoid unnecessary API call
    if task["state"] in constants.TaskState.TERMINAL:
        return {
            "id": str(task["id"]),
            "state": task["state"],
            "message": constants.TaskMessage.ALREADY_TERMINAL.format(
                task["state"].lower()
            ),
        }

    # Call inference service to cancel
    headers = {"X-API-Key": config.settings.inference_api_key}
    async with httpx.AsyncClient() as client:
        response = await client.delete(
            f"{config.settings.inference_service_url}/inference/tasks/{task['inference_task_id']}",
            headers=headers,
            timeout=constants.Defaults.CANCEL_REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()

    # Update task status with what the inference service returns
    postgres_utils.update_task(
        task_id=task_id_int,
        user_id=user_id,
        state=data["state"],  # Will be "REVOKED" from the inference service
        message=constants.TaskMessage.CANCELLED,
        completed_at=sys_utils.get_utc_timestamp(),
    )

    logger.info(
        f"Task cancelled: {task_id_int} for slide {task['slide_id']} by user {user_id}"
    )

    return {
        "id": str(task["id"]),
        "state": data["state"],  # Return what the inference service sent
        "message": constants.TaskMessage.CANCELLED,
    }


async def handle_webhook_callback(
    api_key: str,
    inference_task_id: str,
    state: str,
    message: str,
    timestamp: str,
) -> Dict[str, Any]:
    """
    Handle webhook callback from inference service when task completes.
    Updates the task status in the database.
    """
    # Verify API key is provided and valid
    if not api_key:
        raise ValueError(constants.ErrorMessage.UNAUTHORIZED)

    # Verify the request is from inference service
    if api_key != config.settings.inference_api_key:
        logger.warning(f"Unauthorized webhook attempt with invalid API key")
        raise ValueError(constants.ErrorMessage.UNAUTHORIZED)

    # Convert webhook timestamp to ISO format for consistency
    iso_timestamp = sys_utils.get_utc_timestamp()

    # Update task status
    updated = postgres_utils.update_task_by_inference_task_id(
        inference_task_id=inference_task_id,
        state=state,
        message=message,
        completed_at=iso_timestamp,
    )

    if not updated:
        raise ValueError(constants.ErrorMessage.RESOURCE_NOT_FOUND)

    logger.info(f"Webhook received: task {inference_task_id} updated to {state}")

    return {
        "inference_task_id": inference_task_id,
        "state": state,
        "message": constants.TaskMessage.STATUS_UPDATED,
        "received_at": iso_timestamp,
    }
