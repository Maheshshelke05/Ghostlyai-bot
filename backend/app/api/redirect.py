"""Click-tracking redirect: GET /r/{delivery_id}-{sig} -> 302 to the job's apply link (Chapter 10.4)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import JobDelivery, utcnow
from app.db.session import get_db
from app.services.notifier import parse_tracking_token

router = APIRouter(tags=["redirect"])


@router.get("/r/{token}")
async def redirect_to_job(token: str, db: AsyncSession = Depends(get_db)) -> RedirectResponse:
    delivery_id = parse_tracking_token(token)
    if delivery_id is None:
        raise HTTPException(status_code=404, detail="Link not found")

    delivery = await db.get(JobDelivery, delivery_id)
    if delivery is None:
        raise HTTPException(status_code=404, detail="Link not found")

    if delivery.clicked_at is None:
        delivery.clicked_at = utcnow()
        await db.flush()

    return RedirectResponse(url=delivery.job.apply_link, status_code=302)
