"""Resume file storage.

Uses Cloudinary (as a private "authenticated" asset, delivered only via short-lived signed
URLs - never a public link) whenever CLOUDINARY_URL is configured, since that's required on
hosts with an ephemeral filesystem (Render, Heroku-style). Falls back to local disk under
UPLOAD_DIR when Cloudinary isn't configured, which is fine for a VPS with a persistent volume
or for local development.

resume_path values are tagged so both backends can coexist / be told apart:
  - "cloudinary:<public_id>|<format>"  -> stored in Cloudinary
  - anything else                      -> a local filesystem path
"""
from __future__ import annotations

import asyncio
import io
import time
from pathlib import Path
from typing import Optional

from app.config import settings

_EXT_BY_MIME = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}

_CLOUDINARY_PREFIX = "cloudinary:"
_SIGNED_URL_TTL_SECONDS = 600  # 10 minutes - long enough for an admin to open/download once


def cloudinary_configured() -> bool:
    return bool(settings.CLOUDINARY_URL)


def extension_for(mime: str, fallback_name: str = "") -> str:
    if mime in _EXT_BY_MIME:
        return _EXT_BY_MIME[mime]
    suffix = Path(fallback_name).suffix.lower().lstrip(".")
    return suffix or "bin"


def resume_dir(user_id: int) -> Path:
    return Path(settings.UPLOAD_DIR) / str(user_id)


def _local_resume_path(user_id: int, ext: str) -> Path:
    return resume_dir(user_id) / f"resume.{ext}"


def _write_local_sync(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    for existing in path.parent.glob("resume.*"):
        try:
            existing.unlink()
        except OSError:
            pass
    path.write_bytes(data)


def _delete_local_sync(user_id: int) -> None:
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


def _cloudinary_public_id(user_id: int) -> str:
    return f"resumes/{user_id}/resume"


def _upload_cloudinary_sync(user_id: int, data: bytes, ext: str) -> str:
    import cloudinary.uploader

    public_id = _cloudinary_public_id(user_id)
    cloudinary.uploader.upload(
        io.BytesIO(data),
        public_id=public_id,
        resource_type="raw",
        type="authenticated",
        format=ext,
        overwrite=True,
        invalidate=True,
    )
    return f"{_CLOUDINARY_PREFIX}{public_id}|{ext}"


def _delete_cloudinary_sync(user_id: int) -> None:
    import cloudinary.uploader

    try:
        cloudinary.uploader.destroy(
            _cloudinary_public_id(user_id), resource_type="raw", type="authenticated", invalidate=True
        )
    except Exception:  # noqa: BLE001
        pass  # best-effort - nothing to clean up if it was never uploaded


def _signed_cloudinary_url_sync(public_id: str, ext: str) -> str:
    import cloudinary.utils

    return cloudinary.utils.private_download_url(
        public_id, ext,
        resource_type="raw",
        type="authenticated",
        expires_at=int(time.time()) + _SIGNED_URL_TTL_SECONDS,
    )


def parse_resume_path(resume_path: str) -> tuple[str, str] | None:
    """Returns (public_id, format) if this is a Cloudinary-stored resume, else None."""
    if not resume_path.startswith(_CLOUDINARY_PREFIX):
        return None
    public_id, _, ext = resume_path[len(_CLOUDINARY_PREFIX):].partition("|")
    return public_id, ext


async def save_resume(user_id: int, data: bytes, mime: str, fallback_name: str = "") -> str:
    """Saves a resume and returns the resume_path to store on the Profile row."""
    ext = extension_for(mime, fallback_name)
    if cloudinary_configured():
        return await asyncio.to_thread(_upload_cloudinary_sync, user_id, data, ext)
    path = _local_resume_path(user_id, ext)
    await asyncio.to_thread(_write_local_sync, path, data)
    return str(path)


async def get_resume_url(resume_path: str) -> Optional[str]:
    """A short-lived signed URL for a Cloudinary-stored resume, or None for a local file
    (the caller should serve local files directly instead)."""
    parsed = parse_resume_path(resume_path)
    if parsed is None:
        return None
    public_id, ext = parsed
    return await asyncio.to_thread(_signed_cloudinary_url_sync, public_id, ext)


async def delete_resume(user_id: int, resume_path: Optional[str]) -> None:
    """Deletes a user's stored resume from whichever backend it lives in."""
    if resume_path and parse_resume_path(resume_path) is not None:
        await asyncio.to_thread(_delete_cloudinary_sync, user_id)
    else:
        await asyncio.to_thread(_delete_local_sync, user_id)
