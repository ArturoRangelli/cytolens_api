"""
Copyright (c) 2025 Binary Core LLC. All rights reserved.

This file is part of CytoLens, a proprietary product of Binary Core LLC.
Unauthorized copying, modification, or distribution of this file,
via any medium, is strictly prohibited.

System utilities for file operations and time management
"""

import os
from datetime import datetime


def get_file_ext(filename: str) -> str:
    """
    Extract and return the file extension
    from the given filename.
    """
    _, ext = os.path.splitext(filename.lower())
    return ext


def get_file_size(file_path: str):
    """
    Retrieve the size of a file in bytes.
    """
    return os.path.getsize(file_path)


def get_file_size_text(bytes_value: int) -> str:
    """
    Converts the size of a file at the given file path into a more readable unit
    (Bytes, KB, MB, GB, TB, PB).
    """

    units = ["Bytes", "KB", "MB", "GB", "TB", "PB"]
    size = bytes_value
    i = 0

    while size > 1024 and i < len(units) - 1:
        size /= 1024
        i += 1

    return f"{size:.2f} {units[i]}"


def get_current_time(milliseconds=False) -> str:
    """
    Gets current time
    """
    if milliseconds:
        return datetime.now().strftime("%Y_%m_%d_%H_%M_%S_%f")
    return datetime.now().strftime("%Y/%m/%d %H:%M:%S")


def delete_local_file(file_path: str) -> bool:
    """
    Delete a file from local storage if it exists.
    Returns True if file was deleted, False if file didn't exist.
    """
    if os.path.exists(file_path):
        os.remove(file_path)
        return True
    return False
