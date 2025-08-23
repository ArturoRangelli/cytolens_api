import os
from typing import Dict

from api.schemas.viewer import PredictionsResponse
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


async def get_predictions(slide_id: int, user_id: int) -> Dict:
    """
    Get inference predictions for a slide with bounding boxes.
    Downloads from S3 if not available locally.
    """
    # Check if slide exists and it belongs to the user
    slide_db = postgres_utils.get_slide_by_id(slide_id=slide_id, owner_id=user_id)

    if not slide_db:
        raise ValueError(f"Slide {slide_id} not found")

    pkl_path = os.path.join(config.settings.prediction_dir, f"{slide_id}.pkl")
    
    # Download from S3 if not local
    if not os.path.exists(pkl_path):
        s3_key = f"{config.settings.s3_results_folder}/{slide_id}.pkl"
        os.makedirs(config.settings.prediction_dir, exist_ok=True)
        
        from utils import aws_utils
        
        # Check if file exists in S3
        if not aws_utils.file_exists(
            bucket=config.settings.s3_bucket_name,
            key=s3_key
        ):
            raise ValueError(f"Predictions not found for slide {slide_id}")
        
        # Download from S3
        aws_utils.download_file(
            bucket=config.settings.s3_bucket_name,
            key=s3_key,
            local_path=pkl_path
        )

    ext = slide_db["type"]
    slide_path = os.path.join(config.settings.slide_dir, f"{slide_id}.{ext}")
    _, full_width, full_height, _, _ = slide_utils.get_slide_info_cached(slide_path)
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

    return {
        "segments": segments,
        "wsi_dimensions": {"width": full_width, "height": full_height},
        "classes": {
            "BETHESDA_2": {"color": "#22c55e", "alpha": 0.7},
            "BETHESDA_6": {"color": "#ef4444", "alpha": 0.8},
            "edge": {"color": "#ffffff", "alpha": 0.4},
        },
    }
