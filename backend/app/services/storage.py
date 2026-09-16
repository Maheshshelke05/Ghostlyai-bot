"""Resume file storage on the local /data/resumes volume (never served by nginx directly)."""
from __future__ import annotations

import asyncio
import os
from pathlib import Path

from app.config import settings

_EXT_BY_MIME = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


def extension_for(mime: str, fallback_name: str = "") -> str:
    if mime in _EXT_BY_MIME:
        return _EXT_BY_MIME[mime]
    suffix = Path(fallback_name).suffix.lower()
    return suffix or ".bin"


def resume_dir(user_id: int) -> Path:
    return Path(settings.UPLOAD_DIR) / str(user_id)


def resume_path_for(user_id: int, mime: str, fallback_name: str = "") -> Path:
    return resume_dir(user_id) / f"resume{extension_for(mime, fallback_name)}"


def _write_sync(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Remove any previous resume with a different extension.
    for existing in path.parent.glob("resume.*"):
        try:
            existing.unlink()
        except OSError:
            pass
    path.write_bytes(data)


async def save_resume(user_id: int, data: bytes, mime: str, fallback_name: str = "") -> str:
    path = resume_path_for(user_id, mime, fallback_name)
    await asyncio.to_thread(_write_sync, path, data)
    return str(path)


async def read_resume(path: str) -> bytes | None:
    p = Path(path)
    if not p.exists():
        return None
    return await asyncio.to_thread(p.read_bytes)


async def delete_resume_dir(user_id: int) -> None:
    def _delete() -> None:
        d = resume_dir(user_id)
        if not d.exists():
            return
        for f in d.glob("*"):
            try:
                f.unlink()
            except OSError:
                pass
        try:
            d.rmdir()
        except OSError:
            pass

    await asyncio.to_thread(_delete)
