import math
import pickle

import cucim
import cupy as cp
from cucim.skimage.transform import resize as cp_resize
from nvjpeg import NvJpeg

from utils import constants

nj = NvJpeg()


def _best_slide_level(level_downsamples, ds_needed: float) -> int:
    lvl = 0
    for i, ds in enumerate(level_downsamples):
        if ds <= ds_needed:
            lvl = i
        else:
            break
    return lvl


def gpu_render_tile(
    slide, full_width, full_height, level_downsamples, dz_dims, level, col, row
):
    DZ_LEVELS = len(dz_dims)
    if level < 0 or level >= DZ_LEVELS:
        raise ValueError
    lvl_w, lvl_h = dz_dims[level]
    x, y = col * constants.TILE_SIZE, row * constants.TILE_SIZE
    if x >= lvl_w or y >= lvl_h:
        raise ValueError

    tw, th = min(constants.TILE_SIZE, lvl_w - x), min(constants.TILE_SIZE, lvl_h - y)
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

    if tw != constants.TILE_SIZE or th != constants.TILE_SIZE:
        pad = cp.zeros((constants.TILE_SIZE, constants.TILE_SIZE, 3), dtype=cp.uint8)
        pad[:th, :tw] = gpu_img
        gpu_img = pad

    img_cpu = cp.asnumpy(gpu_img)
    jpeg_bytes = nj.encode(img_cpu, 90)
    return jpeg_bytes


def _load_slide_info(slide_path):
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


def get_slide_info_cached(slide_path):
    if slide_path in constants.SLIDE_INFO_CACHE:
        return constants.SLIDE_INFO_CACHE[slide_path]
    slide_info = _load_slide_info(slide_path)
    constants.SLIDE_INFO_CACHE[slide_path] = slide_info
    return slide_info


def load_inference_file(pkl_path):
    """Load inference results from pickle"""
    with open(pkl_path, "rb") as f:
        return pickle.load(f)
