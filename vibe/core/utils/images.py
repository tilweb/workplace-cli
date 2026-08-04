from __future__ import annotations

import base64
from pathlib import Path

# === ADACOR PATCH: image attachment support (vision) ===

_MEDIA_TYPES: dict[str, str] = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
}

# Cap per image; oversized images are skipped rather than blowing up the request.
MAX_IMAGE_BYTES = 10 * 1024 * 1024


def is_image_path(path: Path) -> bool:
    return path.suffix.lower() in _MEDIA_TYPES


def media_type_for(path: Path) -> str | None:
    return _MEDIA_TYPES.get(path.suffix.lower())


def build_image_data_url(path: Path) -> str | None:
    """Read an image file and return a base64 ``data:`` URL, or None.

    Returns None if the suffix is not a known image type, the file is missing,
    exceeds MAX_IMAGE_BYTES, or cannot be read.
    """
    media_type = media_type_for(path)
    if media_type is None:
        return None
    try:
        if path.stat().st_size > MAX_IMAGE_BYTES:
            return None
        raw = path.read_bytes()
    except OSError:
        return None
    encoded = base64.b64encode(raw).decode("ascii")
    return f"data:{media_type};base64,{encoded}"
