import os

from core import config
from utils import postgres_utils, slide_utils


async def create_dzi(slide_id: int, user_id: int) -> str:
    """
    Generate DZI XML descriptor for the given slide.
    """
    # Get slide from database and verify ownership
    slide_db = postgres_utils.get_slide_by_id(slide_id=slide_id, owner_id=user_id)

    if not slide_db:
        raise ValueError(f"Slide {slide_id} not found")

    ext = slide_db["type"]
    slide_path = os.path.join(config.settings.slide_dir, f"{slide_id}.{ext}")
    _, full_width, full_height, _, _ = slide_utils.get_slide_info_cached(slide_path)

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
        raise ValueError(f"Slide {slide_id} not found")

    ext = slide_db["type"]
    slide_path = os.path.join(config.settings.slide_dir, f"{slide_id}.{ext}")
    slide, full_width, full_height, level_downsamples, dz_dims = (
        slide_utils.get_slide_info_cached(slide_path)
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

    return jpeg_bytes
