"""
Copyright (c) 2025 Binary Core LLC. All rights reserved.

This file is part of CytoLens, a proprietary product of Binary Core LLC.
Unauthorized copying, modification, or distribution of this file,
via any medium, is strictly prohibited.

Inference schemas for AI analysis task management
"""

from typing import List, Optional

from pydantic import BaseModel, Field

from core import constants


class InferenceRequest(BaseModel):
    """Request to start inference"""

    slide_id: int = Field(..., description="ID of the slide to process")
    confidence: float = Field(
        default=constants.Defaults.CONFIDENCE,
        ge=0.0,
        le=0.9,
        description="Confidence threshold for predictions",
    )


class InferenceResponse(BaseModel):
    """Response from starting inference"""

    id: str
    state: str
    message: str


class TaskStatusResponse(BaseModel):
    """Response for task status"""

    id: str
    slide_id: str
    state: str
    message: Optional[str] = None
    confidence: Optional[float] = None
    created_at: str
    completed_at: Optional[str] = None


class TaskCancelResponse(BaseModel):
    """Response for task cancellation"""

    id: str
    state: str
    message: str


class WebhookPayload(BaseModel):
    """Payload received from inference service webhook"""

    inference_task_id: str
    state: str
    timestamp: str  # Datetime string format: "YYYY/MM/DD HH:MM:SS"
    message: str


class SegmentBounds(BaseModel):
    """Computed bounding box of a polygon segment for optimization."""

    minX: float
    maxX: float
    minY: float
    maxY: float


class SegmentPrediction(BaseModel):
    """Individual segmentation prediction with polygon mask."""

    polygon: List[List[float]]  # List of [x, y] coordinates forming the polygon mask
    class_name: str
    score: float  # Confidence score (0-1)
    area: float
    bounds: SegmentBounds  # Computed bounds for spatial indexing/optimization


class WsiDimensions(BaseModel):
    """Whole slide image dimensions."""

    width: int
    height: int


class PredictionsResponse(BaseModel):
    """Response schema for segmentation predictions."""

    segments: List[SegmentPrediction]
    wsi_dimensions: WsiDimensions
