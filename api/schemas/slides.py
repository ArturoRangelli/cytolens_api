"""
Copyright (c) 2025 Binary Core LLC. All rights reserved.

This file is part of CytoLens, a proprietary product of Binary Core LLC.
Unauthorized copying, modification, or distribution of this file,
via any medium, is strictly prohibited.

Slide management schemas for upload, download, and deletion
"""

from typing import List, Optional

from pydantic import BaseModel, field_validator

from core import config
from utils import sys_utils


class Slide(BaseModel):
    """Schema for a single slide"""

    id: int
    name: str
    created_at: str
    owner_id: int
    model_id: int
    original_filename: str
    type: str


class GetSlidesResponse(BaseModel):
    """Schema for get slides response"""

    slides: List[Slide]


class GetSlideResponse(BaseModel):
    """Schema for get single slide response"""

    slide: Optional[Slide] = None


class StartUploadRequest(BaseModel):
    """Schema for starting a slide upload"""

    filename: str
    name: str
    file_size: int

    @field_validator("filename")
    def validate_extension(cls, value: str) -> str:
        ext = sys_utils.get_file_ext(value)
        if ext not in config.settings.allowed_slide_extensions:
            raise ValueError(
                f"Invalid file type. Allowed extensions: {config.settings.allowed_slide_extensions}"
            )
        return value

    @field_validator("file_size")
    def validate_file_size(cls, value: int) -> int:
        if value < config.settings.min_file_size:
            raise ValueError(
                f"File too small. Minimum size is {config.settings.min_file_size / (1024*1024):.0f}MB"
            )
        if value > config.settings.max_file_size:
            raise ValueError(
                f"File too large. Maximum size is {config.settings.max_file_size / (1024*1024*1024):.0f}GB"
            )
        return value


class PresignedUrl(BaseModel):
    """Schema for a presigned URL part"""

    part_number: int
    url: str


class StartUploadResponse(BaseModel):
    """Schema for start upload response"""

    upload_id: str
    s3_key: str
    file_id: str
    part_size: int
    num_parts: int
    presigned_urls: List[PresignedUrl]


class UploadPart(BaseModel):
    """Schema for an upload part with ETag"""

    PartNumber: int
    ETag: str


class FinishUploadRequest(BaseModel):
    """Schema for finishing a slide upload"""

    upload_id: str
    s3_key: str
    parts: List[UploadPart]
    name: str
    model_id: int
    filename: str

    @field_validator("parts")
    def validate_parts(cls, value: List[UploadPart]) -> List[UploadPart]:
        if not value:
            raise ValueError("Parts list cannot be empty")
        return value

    @field_validator("filename")
    def validate_extension(cls, value: str) -> str:
        ext = sys_utils.get_file_ext(value)
        if ext not in config.settings.allowed_slide_extensions:
            raise ValueError(
                f"Invalid file type. Allowed extensions: {config.settings.allowed_slide_extensions}"
            )
        return value

    # Note: model_id validation and name uniqueness check
    # are done in the endpoint/service layer since they need DB access


class FinishUploadResponse(BaseModel):
    """Schema for finish upload response"""

    slide_id: int
    status: str


class CancelUploadRequest(BaseModel):
    """Schema for canceling an upload"""

    upload_id: str
    s3_key: str

    @field_validator("upload_id", "s3_key")
    def validate_not_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("Field cannot be empty")
        return value


class CancelUploadResponse(BaseModel):
    """Schema for cancel upload response"""

    status: str


class DeleteSlideResponse(BaseModel):
    """Schema for delete slide response"""

    message: str


class BulkDeleteRequest(BaseModel):
    """Schema for bulk delete request"""

    slide_ids: List[int]

    @field_validator("slide_ids")
    def validate_slide_ids(cls, value: List[int]) -> List[int]:
        if not value:
            raise ValueError("slide_ids cannot be empty")
        if len(value) > 100:  # Reasonable limit
            raise ValueError("Cannot delete more than 100 slides at once")
        if len(set(value)) != len(value):
            raise ValueError("Duplicate slide IDs not allowed")
        return value


class BulkDeleteResponse(BaseModel):
    """Schema for bulk delete response"""

    message: str
    deleted_count: int
    deleted_ids: List[int]
    failed_ids: List[int]


class UpdateSlideRequest(BaseModel):
    """Schema for updating a slide"""

    name: str

    @field_validator("name")
    def validate_name(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("Name cannot be empty")
        return value.strip()


class UpdateSlideResponse(BaseModel):
    """Schema for update slide response"""

    message: str
    slide: Slide
