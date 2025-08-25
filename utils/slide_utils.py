"""
Copyright (c) 2025 Binary Core LLC. All rights reserved.

This file is part of CytoLens, a proprietary product of Binary Core LLC.
Unauthorized copying, modification, or distribution of this file,
via any medium, is strictly prohibited.

Slide processing utilities for Deep Zoom tile generation
"""

import math
import pickle
import threading
from typing import Any, Dict, List, Tuple

import cucim
import cupy as cp
from cachetools import TTLCache
from cucim.skimage.transform import resize as cp_resize
from nvjpeg import NvJpeg

from core import config

nj = NvJpeg()

# Production cache with TTL (5 minutes) and max size
SLIDE_INFO_CACHE = TTLCache(maxsize=50, ttl=300)
CACHE_LOCK = threading.Lock()  # Thread-safe access


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
