"""GET /admin/meta/districts, GET /admin/meta/job-types."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.admin.deps import current_admin
from app.services.districts import DISTRICTS
from app.services.jobs import JOB_TYPES

router = APIRouter(prefix="/admin/meta", tags=["admin-meta"])


@router.get("/districts")
async def districts(_admin=Depends(current_admin)) -> list[str]:
    return DISTRICTS


@router.get("/job-types")
async def job_types(_admin=Depends(current_admin)) -> list[str]:
    return list(JOB_TYPES)
