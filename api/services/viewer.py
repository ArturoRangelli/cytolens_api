"""
Copyright (c) 2025 Binary Core LLC. All rights reserved.

This file is part of CytoLens, a proprietary product of Binary Core LLC.
Unauthorized copying, modification, or distribution of this file,
via any medium, is strictly prohibited.

Viewer services for Deep Zoom tile serving and predictions
"""

from core import config, constants
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
        raise ValueError(constants.ErrorMessage.RESOURCE_NOT_FOUND)

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
        raise ValueError(constants.ErrorMessage.RESOURCE_NOT_FOUND)

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
