from typing import Dict, List

from fastapi import APIRouter, Depends

from api.dependencies.security import verify_user_access
from api.schemas import inference as inference_schemas
from api.schemas.slides import (
    BulkDeleteRequest,
    BulkDeleteResponse,
    CancelUploadRequest,
    CancelUploadResponse,
    DeleteSlideResponse,
    FinishUploadRequest,
    FinishUploadResponse,
    GetSlideResponse,
    GetSlidesResponse,
    StartUploadRequest,
    StartUploadResponse,
    UpdateSlideRequest,
    UpdateSlideResponse,
)
from api.services import slides as slides_service

router = APIRouter(
    prefix="/slides",
    tags=["slides"],
    responses={404: {"description": "Not found"}},
)


@router.get("", response_model=GetSlidesResponse)
async def get_slides(
    current_user: Dict = Depends(verify_user_access),
) -> GetSlidesResponse:
    """
    Get all slides for the authenticated user.
    Requires authentication via API key or JWT token.
    """
    slides = await slides_service.get_slides(user_id=current_user["id"])
    return GetSlidesResponse(slides=slides)


@router.get("/{slide_id}", response_model=GetSlideResponse)
async def get_slide(
    slide_id: int,
    current_user: Dict = Depends(verify_user_access),
) -> GetSlideResponse:
    """
    Get a single slide by ID.
    Requires authentication and ownership of the slide.
    Returns empty dict if slide not found or user doesn't own it.
    """
    slide = await slides_service.get_slide(
        slide_id=slide_id, user_id=current_user["id"]
    )

    return GetSlideResponse(slide=slide)


@router.get("/{slide_id}/tasks", response_model=List[inference_schemas.TaskStatusResponse])
async def get_slide_tasks(
    slide_id: int,
    current_user: Dict = Depends(verify_user_access),
) -> List[inference_schemas.TaskStatusResponse]:
    """
    Get all inference tasks for a specific slide.
    Returns empty list if slide not found or user doesn't own it.
    """
    tasks = await slides_service.get_slide_tasks(
        slide_id=slide_id, 
        user_id=current_user["id"]
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


@router.post("/upload/start", response_model=StartUploadResponse)
async def start_upload(
    request: StartUploadRequest,
    current_user: Dict = Depends(verify_user_access),
) -> StartUploadResponse:
    """
    Start a new slide upload for large WSI files.
    Validates file type, size, and name uniqueness.
    """
    result = await slides_service.start_upload(
        name=request.name,
        file_size=request.file_size,
        user_id=current_user["id"],
    )

    return StartUploadResponse(
        upload_id=result["upload_id"],
        s3_key=result["s3_key"],
        file_id=result["file_id"],
        part_size=result["part_size"],
        num_parts=result["num_parts"],
        presigned_urls=result["presigned_urls"]
    )


@router.post("/upload/finish", response_model=FinishUploadResponse, status_code=201)
async def finish_upload(
    request: FinishUploadRequest,
    current_user: Dict = Depends(verify_user_access),
) -> FinishUploadResponse:
    """
    Finish the upload and create the slide.
    Validates model_id and name uniqueness before completing.
    """
    result = await slides_service.finish_upload(
        upload_id=request.upload_id,
        s3_key=request.s3_key,
        parts=[part.model_dump() for part in request.parts],
        name=request.name,
        model_id=request.model_id,
        filename=request.filename,
        user_id=current_user["id"],
    )

    return FinishUploadResponse(
        slide_id=result["slide_id"],
        status=result["status"]
    )


@router.post("/upload/cancel", response_model=CancelUploadResponse)
async def cancel_upload(
    request: CancelUploadRequest,
    current_user: Dict = Depends(verify_user_access),
) -> CancelUploadResponse:
    """
    Cancel an ongoing multipart upload.
    Aborts the S3 multipart upload to free up resources.
    Requires authentication via API key or JWT token.
    """
    result = await slides_service.cancel_upload(
        upload_id=request.upload_id,
        s3_key=request.s3_key
    )
    
    return CancelUploadResponse(status=result["status"])


@router.delete("/{slide_id}", response_model=DeleteSlideResponse)
async def delete_slide(
    slide_id: int,
    current_user: Dict = Depends(verify_user_access),
) -> DeleteSlideResponse:
    """
    Delete a slide by ID.
    Removes the slide from database and S3 storage.
    Requires authentication and ownership of the slide.
    """
    result = await slides_service.delete_slide(
        slide_id=slide_id,
        user_id=current_user["id"]
    )
    
    return DeleteSlideResponse(message=result["message"])


@router.patch("/{slide_id}", response_model=UpdateSlideResponse)
async def update_slide(
    slide_id: int,
    request: UpdateSlideRequest,
    current_user: Dict = Depends(verify_user_access),
) -> UpdateSlideResponse:
    """
    Update a slide's name.
    Requires authentication and ownership of the slide.
    Validates name uniqueness for the user.
    """
    result = await slides_service.update_slide(
        slide_id=slide_id,
        name=request.name,
        user_id=current_user["id"]
    )
    
    return UpdateSlideResponse(
        message=result["message"],
        slide=result["slide"]
    )


@router.post("/bulk-delete", response_model=BulkDeleteResponse)
async def bulk_delete_slides(
    request: BulkDeleteRequest,
    current_user: Dict = Depends(verify_user_access),
) -> BulkDeleteResponse:
    """
    Delete multiple slides at once.
    Returns information about successful and failed deletions.
    Requires authentication and ownership of the slides.
    Maximum 100 slides per request.
    """
    result = await slides_service.bulk_delete_slides(
        slide_ids=request.slide_ids,
        user_id=current_user["id"]
    )
    
    return BulkDeleteResponse(
        message=result["message"],
        deleted_count=result["deleted_count"],
        deleted_ids=result["deleted_ids"],
        failed_ids=result["failed_ids"]
    )
