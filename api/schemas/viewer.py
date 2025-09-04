"""
Copyright (c) 2025 Binary Core LLC. All rights reserved.

This file is part of CytoLens, a proprietary product of Binary Core LLC.
Unauthorized copying, modification, or distribution of this file,
via any medium, is strictly prohibited.

Viewer schemas for Deep Zoom tile serving and predictions
"""

from typing import List

from pydantic import BaseModel


class BoundingBox(BaseModel):
    """Bounding box for a segment."""

    minX: float
    maxX: float
    minY: float
    maxY: float


class PredictionSegment(BaseModel):
    """Individual prediction segment with polygon and metadata."""

    polygon: List[List[float]]  # List of [x, y] coordinates
    class_name: str
    score: float  # Confidence score (0-1)
    area: float
    bounds: BoundingBox


class WsiDimensions(BaseModel):
    """Whole slide image dimensions."""

    width: int
    height: int


class PredictionsResponse(BaseModel):
    """Response schema for slide predictions."""

    segments: List[PredictionSegment]
    wsi_dimensions: WsiDimensions
