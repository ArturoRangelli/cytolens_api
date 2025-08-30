"""
Copyright (c) 2025 Binary Core LLC. All rights reserved.

This file is part of CytoLens, a proprietary product of Binary Core LLC.
Unauthorized copying, modification, or distribution of this file,
via any medium, is strictly prohibited.

Viewer services for Deep Zoom tile serving and predictions
"""

import asyncio
from typing import Dict

from core import config
from utils import logging_utils, postgres_utils, slide_utils

logger = logging_utils.get_logger("cytolens.services.viewer")


async def create_dzi(slide_id: int, user_id: int) -> str:
    """
    Generate DZI XML descriptor for the given slide.
    """
    # Get slide from database and verify ownership
    slide_db = postgres_utils.get_slide_by_id(slide_id=slide_id, owner_id=user_id)

    if not slide_db:
        logger.warning(
            f"Unauthorized DZI access attempt for slide {slide_id} by user {user_id}"
        )
        raise ValueError(f"Slide {slide_id} not found")

    ext = slide_db["type"]
    # Ensure slide is available locally (download from S3 if needed)
    # Using async version to prevent blocking other requests during download
    slide_path = await slide_utils.ensure_slide_local_async(slide_id=slide_id, ext=ext)
    _, full_width, full_height, _, _ = slide_utils.get_slide_info_cached(
        slide_path=slide_path
    )

    logger.info(f"DZI accessed for slide {slide_id} by user {user_id}")

    # Build the DZI XML descriptor
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<Image TileSize="{config.settings.tile_size}" '
        f'Overlap="{config.settings.tile_overlap}" '
        f'Format="{config.settings.tile_format}" '
        f'xmlns="http://schemas.microsoft.com/deepzoom/2008">\n'
        f'    <Size Width="{full_width}" Height="{full_height}"/>\n'
        "</Image>"
    )

    return xml


async def get_tile(
    slide_id: int, level: int, col: int, row: int, user_id: int
) -> bytes:
    """
    Render a Deep Zoom tile for a given slide at a specific level, column, and row.
    """
    # Get slide from database and verify ownership
    slide_db = postgres_utils.get_slide_by_id(slide_id=slide_id, owner_id=user_id)

    if not slide_db:
        logger.warning(
            f"Unauthorized tile access attempt for slide {slide_id} by user {user_id}"
        )
        raise ValueError(f"Slide {slide_id} not found")

    ext = slide_db["type"]
    # Ensure slide is available locally (download from S3 if needed)
    # Using async version to prevent blocking other requests during download
    slide_path = await slide_utils.ensure_slide_local_async(slide_id=slide_id, ext=ext)
    slide, full_width, full_height, level_downsamples, dz_dims = (
        slide_utils.get_slide_info_cached(slide_path=slide_path)
    )

    # Render tile using GPU acceleration
    jpeg_bytes = slide_utils.gpu_render_tile(
        slide=slide,
        full_width=full_width,
        full_height=full_height,
        level_downsamples=level_downsamples,
        dz_dims=dz_dims,
        level=level,
        col=col,
        row=row,
    )

    logger.info(
        f"Tile accessed for slide {slide_id} (L{level}/{col}_{row}) by user {user_id}"
    )
    return jpeg_bytes


async def get_predictions(slide_id: int, user_id: int) -> Dict:
    """
    Get inference predictions for a slide with bounding boxes.
    Downloads from S3 if not available locally.
    """
    # Check if slide exists and it belongs to the user
    slide_db = postgres_utils.get_slide_by_id(slide_id=slide_id, owner_id=user_id)

    if not slide_db:
        logger.warning(
            f"Unauthorized predictions access attempt for slide {slide_id} by user {user_id}"
        )
        raise ValueError(f"Slide {slide_id} not found")

    # Ensure predictions are available locally (download from S3 if needed)
    # Using async version to prevent blocking other requests during download
    pkl_path = await slide_utils.ensure_predictions_local_async(slide_id=slide_id)

    ext = slide_db["type"]
    # Ensure slide is also available locally to get dimensions
    slide_path = await slide_utils.ensure_slide_local_async(slide_id=slide_id, ext=ext)
    _, full_width, full_height, _, _ = slide_utils.get_slide_info_cached(
        slide_path=slide_path
    )
    results = slide_utils.load_inference_file(pkl_path=pkl_path)

    # Prepare segments with bounding boxes for efficient rendering
    segments = []
    for seg in results.get("continuous_segments", []):
        polygon = seg["polygon"]
        xs = [p[0] for p in polygon]
        ys = [p[1] for p in polygon]

        segments.append(
            {
                "polygon": polygon,
                "class_name": seg["class_name"],
                "area": seg.get("area", 0),
                "estimated_cells": seg.get("estimated_cells", 0),
                "bounds": {
                    "minX": min(xs),
                    "maxX": max(xs),
                    "minY": min(ys),
                    "maxY": max(ys),
                },
            }
        )

    logger.info(
        f"Predictions accessed for slide {slide_id} by user {user_id} ({len(segments)} segments)"
    )

    return {
        "segments": segments,
        "wsi_dimensions": {"width": full_width, "height": full_height},
        "classes": {
            "BETHESDA_2": {"color": "#22c55e", "alpha": 0.7},
            "BETHESDA_6": {"color": "#ef4444", "alpha": 0.8},
            "edge": {"color": "#ffffff", "alpha": 0.4},
        },
    }
