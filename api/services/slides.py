"""
Copyright (c) 2025 Binary Core LLC. All rights reserved.

This file is part of CytoLens, a proprietary product of Binary Core LLC.
Unauthorized copying, modification, or distribution of this file,
via any medium, is strictly prohibited.

Slide management services for upload, download, and deletion
"""

import math
import os
from typing import Dict, List

from core import config, constants
from utils import aws_utils, logging_utils, postgres_utils, sys_utils

logger = logging_utils.get_logger("cytolens.services.slides")


async def get_slides(user_id: int) -> List[dict]:
    """
    Get all slides for a specific user.
    """
    slides = postgres_utils.get_slides(owner_id=user_id)
    logger.info(f"Slides accessed: {len(slides)} slides retrieved by user {user_id}")
    return slides


async def get_slide(slide_id: int, user_id: int) -> Dict:
    """
    Get a single slide by ID for a specific user.
    Raises ValueError if slide doesn't exist or user doesn't own it.
    """
    slide = postgres_utils.get_slide_by_id(slide_id=slide_id, owner_id=user_id)

    if not slide:
        logger.warning(
            f"Unauthorized slide access attempt for slide {slide_id} by user {user_id}"
        )
        raise ValueError(constants.ErrorMessage.RESOURCE_NOT_FOUND)

    logger.info(f"Slide accessed: {slide_id} by user {user_id}")
    return slide


async def get_slide_tasks(slide_id: int, user_id: int) -> List[Dict]:
    """
    Get all inference tasks for a specific slide.
    Returns empty list if slide doesn't exist or user doesn't own it.
    """
    # Get tasks - ownership is verified in the query via join
    tasks = postgres_utils.get_tasks_by_slide(slide_id=slide_id, user_id=user_id)

    logger.info(
        f"Slide tasks accessed: {len(tasks)} tasks for slide {slide_id} by user {user_id}"
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


async def start_upload(name: str, file_size: int, user_id: int) -> Dict:
    """
    Initialize S3 multipart upload and generate presigned URLs for each part.
    Checks name uniqueness before starting upload.
    """
    # Check if slide name already exists for this user
    existing_slide = postgres_utils.get_slide_by_name(name=name, owner_id=user_id)
    if existing_slide:
        raise ValueError(f"Slide with name '{name}' already exists")

    # Generate unique S3 key
    timestamp = sys_utils.get_current_time(milliseconds=True)
    file_id = f"{user_id}_{timestamp}"
    s3_key = f"{config.settings.s3_temp_slide_folder}/{file_id}"

    # Start multipart upload
    upload_id = aws_utils.create_multipart_upload(
        bucket=config.settings.s3_bucket_name, key=s3_key
    )
    logger.info(
        f"Upload started for slide '{name}' by user {user_id} (upload_id: {upload_id})"
    )

    # Calculate number of parts (100MB per part)
    part_size = 100 * 1024 * 1024  # 100MB
    num_parts = math.ceil(file_size / part_size)

    # Generate presigned URL for each part
    presigned_urls = []
    for part_number in range(1, num_parts + 1):
        presigned_url = aws_utils.generate_multipart_presigned_url(
            bucket=config.settings.s3_bucket_name,
            key=s3_key,
            upload_id=upload_id,
            part_number=part_number,
            expiry=7200,  # 2 hours
        )

        presigned_urls.append({"part_number": part_number, "url": presigned_url})

    return {
        "upload_id": upload_id,
        "s3_key": s3_key,
        "file_id": file_id,
        "part_size": part_size,
        "num_parts": num_parts,
        "presigned_urls": presigned_urls,
    }


async def finish_upload(
    upload_id: str,
    s3_key: str,
    parts: List[Dict],
    name: str,
    model_id: int,
    filename: str,
    user_id: int,
) -> Dict:
    """
    Complete the multipart upload and create slide record.
    Validates model_id exists and name is unique.
    """
    # Validate model_id exists
    model = postgres_utils.get_model(model_id=model_id)
    if not model:
        raise ValueError(f"Model with id {model_id} does not exist")

    # Check if slide name already exists for this user
    existing_slide = postgres_utils.get_slide_by_name(name=name, owner_id=user_id)
    if existing_slide:
        raise ValueError(f"Slide with name '{name}' already exists")

    # Complete S3 multipart upload
    aws_utils.complete_multipart_upload(
        bucket=config.settings.s3_bucket_name,
        key=s3_key,
        upload_id=upload_id,
        parts=parts,
    )

    # Get the actual file size from S3
    file_size = aws_utils.get_object_size(
        bucket=config.settings.s3_bucket_name, key=s3_key
    )

    # Create slide record
    created_at = sys_utils.get_utc_timestamp()
    ext = sys_utils.get_file_ext(filename=filename).replace(".", "")

    slide = postgres_utils.set_slide(
        name=name,
        model_id=model_id,
        owner_id=user_id,
        created_at=created_at,
        original_filename=filename,
        type=ext,
        file_size=file_size,
    )

    # Move from temp to permanent S3 location
    permanent_key = f"{config.settings.s3_slide_folder}/{slide['id']}.{ext}"

    aws_utils.copy_file(
        bucket=config.settings.s3_bucket_name, key_src=s3_key, key_dst=permanent_key
    )

    aws_utils.delete_file(bucket=config.settings.s3_bucket_name, key=s3_key)

    logger.info(f"Slide uploaded: '{name}' (ID: {slide['id']}) by user {user_id}")

    return {"slide_id": slide["id"], "status": "ready"}


async def cancel_upload(upload_id: str, s3_key: str) -> Dict:
    """
    Abort a multipart upload and clean up.
    """
    aws_utils.abort_multipart_upload(
        bucket=config.settings.s3_bucket_name, key=s3_key, upload_id=upload_id
    )
    logger.info(f"Upload cancelled: upload_id {upload_id}")
    return {"status": "aborted"}


async def delete_slide(slide_id: int, user_id: int) -> Dict:
    """
    Delete a slide from database and S3.
    Checks ownership before deletion.
    Gracefully handles missing S3 files.
    """
    # Step 1: Get slide from DB and verify ownership
    slide = postgres_utils.get_slide_by_id(slide_id=slide_id, owner_id=user_id)

    if not slide:
        logger.warning(
            f"Unauthorized delete attempt for slide {slide_id} by user {user_id}"
        )
        raise ValueError(constants.ErrorMessage.RESOURCE_NOT_FOUND)

    # Step 2: Build S3 keys for both possible locations
    file_ext = slide.get("type", "svs")
    permanent_s3_key = f"{config.settings.s3_slide_folder}/{slide_id}.{file_ext}"

    # Step 3: Delete slide from S3 (if exists)
    if aws_utils.file_exists(
        bucket=config.settings.s3_bucket_name, key=permanent_s3_key
    ):
        aws_utils.delete_file(
            bucket=config.settings.s3_bucket_name, key=permanent_s3_key
        )

    # Step 4: Delete predictions from S3 (if exists)
    predictions_s3_key = f"{config.settings.s3_results_folder}/{slide_id}.pkl"
    if aws_utils.file_exists(
        bucket=config.settings.s3_bucket_name, key=predictions_s3_key
    ):
        aws_utils.delete_file(
            bucket=config.settings.s3_bucket_name, key=predictions_s3_key
        )

    # Step 5: Delete from local storage (if exists)
    local_path = os.path.join(config.settings.slide_dir, f"{slide_id}.{file_ext}")
    sys_utils.delete_local_file(local_path)

    # Step 6: Delete predictions from local storage (if exists)
    pkl_path = os.path.join(config.settings.prediction_dir, f"{slide_id}.pkl")
    sys_utils.delete_local_file(pkl_path)

    # Step 7: Delete from database
    postgres_utils.delete_slide(slide_id=slide_id, owner_id=user_id)

    logger.info(f"Slide deleted: {slide_id} by user {user_id}")

    # Step 8: Return success message
    return {"message": f"Slide {slide_id} deleted successfully"}


async def bulk_delete_slides(slide_ids: List[int], user_id: int) -> Dict:
    """
    Delete multiple slides at once.
    Returns information about which slides were deleted and which failed.
    """
    deleted_ids = []
    failed_ids = []

    for slide_id in slide_ids:
        # Get slide info first
        slide = postgres_utils.get_slide_by_id(slide_id=slide_id, owner_id=user_id)

        if not slide:
            failed_ids.append(slide_id)
            continue

        # Build S3 key
        file_ext = slide.get("type", "svs")
        permanent_s3_key = f"{config.settings.s3_slide_folder}/{slide_id}.{file_ext}"

        # Delete slide from S3 (if exists)
        if aws_utils.file_exists(
            bucket=config.settings.s3_bucket_name, key=permanent_s3_key
        ):
            aws_utils.delete_file(
                bucket=config.settings.s3_bucket_name, key=permanent_s3_key
            )

        # Delete predictions from S3 (if exists)
        predictions_s3_key = f"{config.settings.s3_results_folder}/{slide_id}.pkl"
        if aws_utils.file_exists(
            bucket=config.settings.s3_bucket_name, key=predictions_s3_key
        ):
            aws_utils.delete_file(
                bucket=config.settings.s3_bucket_name, key=predictions_s3_key
            )

        # Delete from local storage (if exists)
        local_path = os.path.join(config.settings.slide_dir, f"{slide_id}.{file_ext}")
        sys_utils.delete_local_file(local_path)

        # Delete predictions from local storage (if exists)
        pkl_path = os.path.join(config.settings.prediction_dir, f"{slide_id}.pkl")
        sys_utils.delete_local_file(pkl_path)

        # Delete from database
        postgres_utils.delete_slide(slide_id=slide_id, owner_id=user_id)
        deleted_ids.append(slide_id)

    if deleted_ids:
        logger.info(
            f"Bulk delete: {len(deleted_ids)} slides deleted by user {user_id} (IDs: {deleted_ids})"
        )
    if failed_ids:
        logger.warning(
            f"Bulk delete failed: {len(failed_ids)} slides not found for user {user_id} (IDs: {failed_ids})"
        )

    return {
        "message": f"Bulk delete completed. {len(deleted_ids)} slides deleted.",
        "deleted_count": len(deleted_ids),
        "deleted_ids": deleted_ids,
        "failed_ids": failed_ids,
    }


async def update_slide(slide_id: int, name: str, user_id: int) -> Dict:
    """
    Update a slide's name.
    Checks ownership and name uniqueness before updating.
    """
    # Step 1: Check if slide exists and user owns it
    slide = postgres_utils.get_slide_by_id(slide_id=slide_id, owner_id=user_id)

    if not slide:
        logger.warning(
            f"Unauthorized update attempt for slide {slide_id} by user {user_id}"
        )
        raise ValueError(constants.ErrorMessage.RESOURCE_NOT_FOUND)

    # Step 2: If the name is the same, no need to update
    if slide["name"] == name:
        return {"message": "Slide name unchanged", "slide": slide}

    # Step 3: Check if new name already exists for this user
    existing_slide = postgres_utils.get_slide_by_name(name=name, owner_id=user_id)
    if existing_slide and existing_slide["id"] != slide_id:
        raise ValueError(f"Slide with name '{name}' already exists")

    # Step 4: Update the slide name
    updated_slide = postgres_utils.update_slide(
        slide_id=slide_id, owner_id=user_id, name=name
    )

    if not updated_slide:
        raise ValueError(constants.ErrorMessage.UPDATE_FAILED)

    logger.info(f"Slide updated: {slide_id} renamed to '{name}' by user {user_id}")

    return {"message": f"Slide {slide_id} updated successfully", "slide": updated_slide}
