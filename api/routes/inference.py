"""
Copyright (c) 2025 Binary Core LLC. All rights reserved.

This file is part of CytoLens, a proprietary product of Binary Core LLC.
Unauthorized copying, modification, or distribution of this file,
via any medium, is strictly prohibited.

Inference routes for managing AI analysis tasks
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, Header, Query

from api.dependencies.security import verify_user_access
from api.schemas import inference as inference_schemas
from api.services import inference as inference_service
from core import constants

router = APIRouter(
    prefix="/inference",
    tags=["inference"],
    responses={404: {"description": "Not found"}},
)


@router.post("", response_model=inference_schemas.InferenceResponse)
async def start_inference(
    request: inference_schemas.InferenceRequest,
    current_user: dict = Depends(verify_user_access),
) -> inference_schemas.InferenceResponse:
    """
    Start inference for a slide.
    Returns task_id that can be used to check status.
    """
    result = await inference_service.start_inference(
        slide_id=request.slide_id,
        user_id=current_user["id"],
        confidence=request.confidence,
    )
    return inference_schemas.InferenceResponse(
        id=result["id"],
        state=result["state"],
        message=result["message"],
    )


@router.get("/tasks", response_model=List[inference_schemas.TaskStatusResponse])
async def get_tasks(
    current_user: dict = Depends(verify_user_access),
    state: Optional[str] = Query(None, description="Filter by task state"),
    limit: int = Query(
        constants.Defaults.TASK_LIMIT,
        ge=1,
        le=100,
        description="Number of tasks to return",
    ),
    offset: int = Query(
        constants.Defaults.TASK_OFFSET, ge=0, description="Number of tasks to skip"
    ),
) -> List[inference_schemas.TaskStatusResponse]:
    """
    Get all inference tasks for the current user.
    """
    tasks = await inference_service.get_tasks(
        user_id=current_user["id"], state=state, limit=limit, offset=offset
    )
    return [
        inference_schemas.TaskStatusResponse(
            id=task["id"],
            slide_id=task["slide_id"],
            state=task["state"],
            message=task.get("message"),
            confidence=task.get("confidence"),
            created_at=task["created_at"],
            completed_at=task.get("completed_at"),
        )
        for task in tasks
    ]


@router.get("/tasks/{task_id}", response_model=inference_schemas.TaskStatusResponse)
async def get_task_status(
    task_id: str,
    current_user: dict = Depends(verify_user_access),
) -> inference_schemas.TaskStatusResponse:
    """
    Get the status of an inference task.
    """
    result = await inference_service.get_task_status(
        task_id=task_id, user_id=current_user["id"]
    )
    return inference_schemas.TaskStatusResponse(
        id=result["id"],
        slide_id=result["slide_id"],
        state=result["state"],
        message=result["message"],
        confidence=result["confidence"],
        created_at=result["created_at"],
        completed_at=result["completed_at"],
    )


@router.delete("/tasks/{task_id}", response_model=inference_schemas.TaskCancelResponse)
async def cancel_task(
    task_id: str,
    current_user: dict = Depends(verify_user_access),
) -> inference_schemas.TaskCancelResponse:
    """
    Cancel an inference task.
    """
    result = await inference_service.cancel_task(
        task_id=task_id, user_id=current_user["id"]
    )
    return inference_schemas.TaskCancelResponse(
        id=result["id"], state=result["state"], message=result["message"]
    )


@router.post("/webhook/callback")
async def inference_webhook(
    payload: inference_schemas.WebhookPayload,
    x_api_key: str = Header(None, alias="X-API-Key"),
):
    """
    Webhook callback from inference service when task completes.
    Updates the task status in the database.
    """
    result = await inference_service.handle_webhook_callback(
        api_key=x_api_key,
        inference_task_id=payload.inference_task_id,
        state=payload.state,
        message=payload.message,
        timestamp=payload.timestamp,
    )
    return result
