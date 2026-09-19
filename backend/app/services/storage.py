"""Resume file storage.

Uses Cloudinary (as a private "authenticated" asset, delivered only via short-lived signed
URLs - never a public link) whenever CLOUDINARY_URL is configured, since that's required on
hosts with an ephemeral filesystem. Falls back to local disk under UPLOAD_DIR when Cloudinary
isn't configured, which is fine for a VPS with a persistent volume or for local development.

Cloudinary quirk this module works around: for resource_type="raw", the file's extension is
part of its public_id's identity (Cloudinary appends `format` onto `public_id` at upload time
but does NOT reliably do the same lookup when generating a private_download_url from a bare
public_id + separate format - that mismatch 404s). So the extension is always embedded directly
in the public_id we choose, and reused as-is for delete/download - no guessing involved.

resume_path values are tagged so both backends can coexist / be told apart:
  - "cloudinary:<public_id incl. extension>"  -> stored in Cloudinary
  - anything else                             -> a local filesystem path
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


def _cloudinary_public_id(user_id: int, ext: str) -> str:
    return f"resumes/{user_id}/resume.{ext}"


def _upload_cloudinary_sync(user_id: int, data: bytes, ext: str) -> str:
    import cloudinary.uploader

    public_id = _cloudinary_public_id(user_id, ext)
    cloudinary.uploader.upload(
        io.BytesIO(data),
        public_id=public_id,
        resource_type="raw",
        type="authenticated",
        overwrite=True,
        invalidate=True,
    )
    return f"{_CLOUDINARY_PREFIX}{public_id}"


def _delete_cloudinary_sync(public_id: str) -> None:
    import cloudinary.uploader

    try:
        cloudinary.uploader.destroy(public_id, resource_type="raw", type="authenticated", invalidate=True)
    except Exception:  # noqa: BLE001
        pass  # best-effort - nothing to clean up if it was never uploaded


def _signed_cloudinary_url_sync(public_id: str) -> str:
    import cloudinary.utils

    return cloudinary.utils.private_download_url(
        public_id, "",  # format is already embedded in public_id for raw resources
        resource_type="raw",
        type="authenticated",
        expires_at=int(time.time()) + _SIGNED_URL_TTL_SECONDS,
    )


def parse_resume_path(resume_path: str) -> Optional[str]:
    """Returns the Cloudinary public_id if this is a Cloudinary-stored resume, else None."""
    if not resume_path.startswith(_CLOUDINARY_PREFIX):
        return None
    return resume_path[len(_CLOUDINARY_PREFIX):]


async def save_resume(
    user_id: int, data: bytes, mime: str, fallback_name: str = "",
    previous_resume_path: Optional[str] = None,
) -> str:
    """Saves a resume and returns the resume_path to store on the Profile row.

    `previous_resume_path` (the profile's existing resume_path, if any) is used to clean up a
    prior upload with a different extension - Cloudinary's overwrite only replaces a resource
    with the exact same public_id, so a PDF-then-DOCX re-upload would otherwise leave the old
    PDF behind as an orphaned resource.
    """
    ext = extension_for(mime, fallback_name)
    if cloudinary_configured():
        if previous_resume_path:
            old_public_id = parse_resume_path(previous_resume_path)
            new_public_id = _cloudinary_public_id(user_id, ext)
            if old_public_id and old_public_id != new_public_id:
                await asyncio.to_thread(_delete_cloudinary_sync, old_public_id)
        return await asyncio.to_thread(_upload_cloudinary_sync, user_id, data, ext)
    path = _local_resume_path(user_id, ext)
    await asyncio.to_thread(_write_local_sync, path, data)
    return str(path)


async def get_resume_url(resume_path: str) -> Optional[str]:
    """A short-lived signed URL for a Cloudinary-stored resume, or None for a local file
    (the caller should serve local files directly instead)."""
    public_id = parse_resume_path(resume_path)
    if public_id is None:
        return None
    return await asyncio.to_thread(_signed_cloudinary_url_sync, public_id)


async def delete_resume(user_id: int, resume_path: Optional[str]) -> None:
    """Deletes a user's stored resume from whichever backend it lives in."""
    public_id = parse_resume_path(resume_path) if resume_path else None
    if public_id:
        await asyncio.to_thread(_delete_cloudinary_sync, public_id)
    else:
        await asyncio.to_thread(_delete_local_sync, user_id)


# ---------------------------------------------------------------------------
# Support message image attachments - separate namespace from resumes (one file per
# message, not one per user; resource_type="image" not "raw"), same authenticated/signed-URL
# treatment since a screenshot can carry personal info same as a resume.
# ---------------------------------------------------------------------------
_IMAGE_MIMES = {"image/jpeg", "image/png", "image/webp"}


def is_supported_image_mime(mime: str) -> bool:
    return mime in _IMAGE_MIMES


def _support_image_dir() -> Path:
    return Path(settings.UPLOAD_DIR) / "support"


def _local_support_image_path(message_id: int, ext: str) -> Path:
    return _support_image_dir() / f"{message_id}.{ext}"


def _cloudinary_support_public_id(message_id: int, ext: str) -> str:
    return f"support/{message_id}.{ext}"


def _upload_support_image_cloudinary_sync(message_id: int, data: bytes, ext: str) -> str:
    import cloudinary.uploader

    public_id = _cloudinary_support_public_id(message_id, ext)
    cloudinary.uploader.upload(
        io.BytesIO(data), public_id=public_id, resource_type="image",
        type="authenticated", overwrite=True, invalidate=True,
    )
    return f"{_CLOUDINARY_PREFIX}{public_id}"


def _signed_support_image_url_sync(public_id: str) -> str:
    import cloudinary.utils

    url, _options = cloudinary.utils.cloudinary_url(
        public_id, resource_type="image", type="authenticated", sign_url=True, secure=True,
    )
    return url


async def save_support_image(message_id: int, data: bytes, mime: str) -> str:
    """Saves a support-message image and returns the path to store on the message row."""
    ext = extension_for(mime)
    if cloudinary_configured():
        return await asyncio.to_thread(_upload_support_image_cloudinary_sync, message_id, data, ext)
    path = _local_support_image_path(message_id, ext)
    await asyncio.to_thread(_write_local_sync, path, data)
    return str(path)


async def get_support_image_url(image_path: str) -> Optional[str]:
    """A signed URL for a Cloudinary-stored image, or None for a local file (the caller
    should serve local files directly instead)."""
    public_id = parse_resume_path(image_path)
    if public_id is None:
        return None
    return await asyncio.to_thread(_signed_support_image_url_sync, public_id)
