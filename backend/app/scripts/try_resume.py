"""Manual test helper: parse one or more resume files with Gemini and print the JSON.

Usage:
    python -m app.scripts.try_resume path/to/file.pdf [more/files.docx ...]
    python -m app.scripts.try_resume path/to/folder/
"""
from __future__ import annotations

import asyncio
import json
import mimetypes
import sys
from pathlib import Path

from sqlalchemy import select

from app.db.models import Category
from app.db.session import SessionLocal
from app.services.ai import parse_resume

_MIME_OVERRIDES = {
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def _guess_mime(path: Path) -> str:
    if path.suffix.lower() in _MIME_OVERRIDES:
        return _MIME_OVERRIDES[path.suffix.lower()]
    mime, _ = mimetypes.guess_type(str(path))
    return mime or "application/octet-stream"


async def _main(paths: list[str]) -> None:
    files: list[Path] = []
    for p in paths:
        path = Path(p)
        if path.is_dir():
            files.extend(sorted(path.iterdir()))
        else:
            files.append(path)

    async with SessionLocal() as db:
        rows = (await db.execute(select(Category).where(Category.is_active))).scalars().all()
        categories = {c.slug: c.name for c in rows}

    for path in files:
        if not path.is_file():
            continue
        data = path.read_bytes()
        mime = _guess_mime(path)
        print(f"\n=== {path.name} ({mime}) ===")
        result = await parse_resume(data, mime, categories)
        if result is None:
            print("  -> FAILED to parse")
            continue
        print(json.dumps(result.model_dump(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    asyncio.run(_main(sys.argv[1:]))
