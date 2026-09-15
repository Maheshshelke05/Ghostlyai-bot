"""Interactive script to create an admin (owner or uploader) account.

Usage (inside the api container or a local venv with DATABASE_URL set):
    python -m app.scripts.create_admin
"""
from __future__ import annotations

import asyncio
import getpass

from sqlalchemy import select

from app.db.models import Admin
from app.db.session import SessionLocal
from app.services.auth import hash_password


async def _main() -> None:
    print("Create admin account")
    name = input("Name: ").strip()
    email = input("Email: ").strip().lower()
    role = (input("Role [owner/uploader] (default owner): ").strip() or "owner").lower()
    if role not in ("owner", "uploader"):
        print("Role must be 'owner' or 'uploader'.")
        return
    password = getpass.getpass("Password: ")
    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        print("Passwords do not match.")
        return
    if len(password) < 8:
        print("Password must be at least 8 characters.")
        return

    async with SessionLocal() as db:
        existing = (
            await db.execute(select(Admin).where(Admin.email == email))
        ).scalar_one_or_none()
        if existing:
            print(f"An admin with email {email} already exists.")
            return
        admin = Admin(
            name=name, email=email, password_hash=hash_password(password),
            role=role, is_active=True,
        )
        db.add(admin)
        await db.commit()
        print(f"Admin '{name}' <{email}> ({role}) created.")


if __name__ == "__main__":
    asyncio.run(_main())
