"""
Copyright (c) 2025 Binary Core LLC. All rights reserved.

This file is part of CytoLens, a proprietary product of Binary Core LLC.
Unauthorized copying, modification, or distribution of this file,
via any medium, is strictly prohibited.

Slide processing utilities for Deep Zoom tile generation
"""

import asyncio
import math
import os
import pickle
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Tuple

import cucim
import cupy as cp
from cachetools import TTLCache
from cucim.skimage.transform import resize as cp_resize
from nvjpeg import NvJpeg

from core import config
from utils import aws_utils

nj = NvJpeg()

# Thread pool for blocking I/O operations to prevent blocking the event loop
_executor = ThreadPoolExecutor(max_workers=4)

# Production cache with TTL (5 minutes) and max size
SLIDE_INFO_CACHE = TTLCache(maxsize=50, ttl=300)
CACHE_LOCK = threading.Lock()  # Thread-safe access

# Track downloads in progress with asyncio Events for coordination
_downloads_in_progress = {}  # key -> asyncio.Event
_downloads_lock = threading.Lock()


def _best_slide_level(level_downsamples: List[float], ds_needed: float) -> int:
    """Find best pyramid level for downsampling."""
    lvl = 0
    for i, ds in enumerate(level_downsamples):
        if ds <= ds_needed:
            lvl = i
        else:
            break
    return lvl


def _load_slide_info(
    slide_path: str,
) -> Tuple[Any, int, int, List[float], List[Tuple[int, int]]]:
    """Load slide and calculate Deep Zoom dimensions."""
    slide = cucim.CuImage(slide_path)
    full_width, full_height = slide.resolutions["level_dimensions"][0]
    level_downsamples = slide.resolutions["level_downsamples"]

    max_dim = max(full_width, full_height)
    max_level = math.ceil(math.log2(max_dim))
    dz_dims = []

    for level in range(0, max_level + 1):
        scale = 2 ** (max_level - level)
        w = math.ceil(full_width / scale)
        h = math.ceil(full_height / scale)
        dz_dims.append((w, h))

    return slide, full_width, full_height, level_downsamples, dz_dims


def _download_predictions_from_s3(slide_id: int) -> str:
    """
    Download predictions from S3 to local storage.
    This function ONLY handles the download, no checking.
    """
    pkl_path = os.path.join(config.settings.prediction_dir, f"{slide_id}.pkl")
    s3_key = f"{config.settings.s3_results_folder}/{slide_id}.pkl"

    # Create directory if needed
    os.makedirs(config.settings.prediction_dir, exist_ok=True)

    # Check if exists in S3
    if not aws_utils.file_exists(bucket=config.settings.s3_bucket_name, key=s3_key):
        raise ValueError(f"Predictions not found for slide {slide_id}")

    # Download from S3
    aws_utils.download_file(
        bucket=config.settings.s3_bucket_name, key=s3_key, local_path=pkl_path
    )

    return pkl_path


def _download_slide_from_s3(slide_id: int, ext: str) -> str:
    """
    Download slide from S3 to local storage.
    This function ONLY handles the download, no checking.
    """
    local_path = os.path.join(config.settings.slide_dir, f"{slide_id}.{ext}")
    s3_key = f"{config.settings.s3_slide_folder}/{slide_id}.{ext}"

    # Create directory if needed
    os.makedirs(config.settings.slide_dir, exist_ok=True)

    # Check if exists in S3
    if not aws_utils.file_exists(bucket=config.settings.s3_bucket_name, key=s3_key):
        raise ValueError(f"Slide {slide_id} not found in storage")

    # Download from S3
    aws_utils.download_file(
        bucket=config.settings.s3_bucket_name, key=s3_key, local_path=local_path
    )

    return local_path


def gpu_render_tile(
    slide: Any,
    full_width: int,
    full_height: int,
    level_downsamples: List[float],
    dz_dims: List[Tuple[int, int]],
    level: int,
    col: int,
    row: int,
) -> bytes:
    """Render a tile using GPU acceleration."""
    DZ_LEVELS = len(dz_dims)
    if level < 0 or level >= DZ_LEVELS:
        raise ValueError
    lvl_w, lvl_h = dz_dims[level]
    x, y = col * config.settings.tile_size, row * config.settings.tile_size
    if x >= lvl_w or y >= lvl_h:
        raise ValueError

    tw, th = min(config.settings.tile_size, lvl_w - x), min(
        config.settings.tile_size, lvl_h - y
    )
    scale_x, scale_y = full_width / lvl_w, full_height / lvl_h
    bx, by = int(x * scale_x), int(y * scale_y)
    bw, bh = int(math.ceil(tw * scale_x)), int(math.ceil(th * scale_y))

    slide_lvl = _best_slide_level(level_downsamples, max(scale_x, scale_y))
    ds = level_downsamples[slide_lvl]
    rw, rh = math.ceil(bw / ds), math.ceil(bh / ds)

    region = slide.read_region(location=(bx, by), size=(rw, rh), level=slide_lvl)
    gpu_img = cp.asarray(region)[:, :, ::-1]

    if (gpu_img.shape[1], gpu_img.shape[0]) != (tw, th):
        gpu_img = cp_resize(gpu_img, output_shape=(th, tw), preserve_range=True).astype(
            cp.uint8
        )

    if tw != config.settings.tile_size or th != config.settings.tile_size:
        pad = cp.zeros(
            (config.settings.tile_size, config.settings.tile_size, 3), dtype=cp.uint8
        )
        pad[:th, :tw] = gpu_img
        gpu_img = pad

    img_cpu = cp.asnumpy(gpu_img)
    jpeg_bytes = nj.encode(img_cpu, 90)
    return jpeg_bytes


def get_slide_info_cached(
    slide_path: str,
) -> Tuple[Any, int, int, List[float], List[Tuple[int, int]]]:
    """
    Get slide info from cache or load if not cached.
    Thread-safe with TTL-based expiration.
    """
    with CACHE_LOCK:
        # Try to get from cache
        if slide_path in SLIDE_INFO_CACHE:
            return SLIDE_INFO_CACHE[slide_path]

        # Cache miss - load the slide
        slide_info = _load_slide_info(slide_path)
        SLIDE_INFO_CACHE[slide_path] = slide_info
        return slide_info


def get_cache_info() -> Dict[str, Any]:
    """Get cache statistics for monitoring."""
    with CACHE_LOCK:
        return {
            "current_size": len(SLIDE_INFO_CACHE),
            "max_size": SLIDE_INFO_CACHE.maxsize,
            "ttl_seconds": SLIDE_INFO_CACHE.ttl,
            "cached_paths": list(SLIDE_INFO_CACHE.keys()),
        }


def clear_cache() -> None:
    """Clear the slide cache (for maintenance)."""
    with CACHE_LOCK:
        SLIDE_INFO_CACHE.clear()


def load_inference_file(pkl_path: str) -> Any:
    """Load inference results from pickle file."""
    with open(pkl_path, "rb") as f:
        return pickle.load(f)


async def ensure_slide_local_async(slide_id: int, ext: str) -> str:
    """
    Ensures a slide is available locally, downloading from S3 if needed.

    When multiple requests ask for the same slide:
    - First request downloads the file
    - Subsequent requests wait for the download to complete
    - All requests return the same result

    This prevents duplicate downloads while keeping the server responsive.
    """
    local_path = os.path.join(config.settings.slide_dir, f"{slide_id}.{ext}")

    # Fast path: slide already exists locally
    if os.path.exists(local_path):
        return local_path

    # Coordinate with other potential downloads of the same slide
    download_key = f"slide_{slide_id}_{ext}"

    # Determine if we should download or wait for another request's download
    download_event = None
    i_should_download = False

    with _downloads_lock:
        if download_key in _downloads_in_progress:
            # Another request is already downloading this slide
            download_event = _downloads_in_progress[download_key]
        else:
            # We'll download it and let others know when we're done
            download_event = asyncio.Event()
            _downloads_in_progress[download_key] = download_event
            i_should_download = True

    # Path 1: We're responsible for downloading the slide
    if i_should_download:
        try:
            # Double-check the file doesn't exist (race condition prevention)
            if not os.path.exists(local_path):
                # Perform the actual download in a thread pool (non-blocking)
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    _executor,
                    _download_slide_from_s3,
                    slide_id,
                    ext,
                )

            # Notify all waiting requests that the download is complete
            download_event.set()
            return local_path

        except Exception as e:
            # Notify waiters even on failure (prevents hanging)
            download_event.set()
            raise e

        finally:
            # Clean up the download tracker
            with _downloads_lock:
                _downloads_in_progress.pop(download_key, None)

    # Path 2: Another request is downloading, we wait for it
    else:
        # Wait for the download to complete (async, non-blocking)
        await download_event.wait()

        # Verify the file now exists
        if os.path.exists(local_path):
            return local_path
        else:
            # The download failed in the other request
            raise ValueError(f"Download of slide {slide_id} failed in another request")


def ensure_predictions_local(slide_id: int) -> str:
    """
    Ensures prediction results are available locally, downloading from S3 if needed.
    Simple synchronous version since pkl files are small.
    """
    pkl_path = os.path.join(config.settings.prediction_dir, f"{slide_id}.pkl")

    # If predictions already exist locally, return the path
    # TODO: we will need to save prediction files with multiple names for
    # the same slide, one slide can have multiple taks = multiple prediction files
    # if os.path.exists(pkl_path):
    #     return pkl_path

    # Download from S3 if not present locally
    _download_predictions_from_s3(slide_id)

    return pkl_path
