"""File handling helpers for uploads and temp storage."""

import os
import uuid
from typing import Optional

import structlog
from werkzeug.utils import secure_filename

from config import ALLOWED_UPLOAD_EXTENSIONS, temp_storage_path

log = structlog.get_logger()

_MAGIC = {
    b"\x89PNG\r\n\x1a\n": ".png",
    b"\xff\xd8\xff": ".jpg",
    b"%PDF": ".pdf",
}


def allowed_file(filename: str) -> bool:
    return os.path.splitext(filename or "")[1].lower() in ALLOWED_UPLOAD_EXTENSIONS


def sniff_extension(path: str) -> Optional[str]:
    """Detect real file type from magic bytes (extension can lie)."""
    try:
        with open(path, "rb") as f:
            head = f.read(8)
    except OSError:
        return None
    for magic, ext in _MAGIC.items():
        if head.startswith(magic):
            return ext
    return None


def save_uploaded_file(file_storage, ext: str) -> str:
    """Persist a Werkzeug FileStorage to the temp directory under a random name."""
    temp_dir = temp_storage_path()
    os.makedirs(temp_dir, exist_ok=True)
    ext = ext if ext.startswith(".") else f".{ext}"
    safe_stem = secure_filename(os.path.splitext(file_storage.filename or "upload")[0])[:40] or "upload"
    path = os.path.join(temp_dir, f"{safe_stem}-{uuid.uuid4().hex}{ext.lower()}")
    file_storage.save(path)
    log.info("upload_saved", path=path)
    return path


def cleanup_temp_file(path: Optional[str]) -> None:
    if not path:
        return
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError as e:
        log.warning("temp_cleanup_failed", path=path, error=str(e))
