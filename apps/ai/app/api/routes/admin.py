from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.db.session import get_db
from app.models.analytics import AnalyticsEvent, BackgroundJob
from app.models.user import User
from app.worker.tasks.download_images_task import download_card_images_task
from app.worker.tasks.embed_tasks import embed_cards_task
from app.worker.tasks.import_tasks import import_cards_task
from app.worker.tasks.scrape_tasks import scrape_source_task

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/scrape/run")
async def run_scrape(
    source_id: str | None = None,
    admin: User = Depends(require_admin),
):
    task = scrape_source_task.delay(source_id=source_id)
    return {"task_id": task.id, "status": "queued"}


@router.post("/import/cards")
async def import_cards(
    limit: int | None = None,
    admin: User = Depends(require_admin),
):
    task = import_cards_task.delay(limit=limit)
    return {"task_id": task.id, "status": "queued"}


@router.post("/index/embed")
async def rebuild_embeddings(
    admin: User = Depends(require_admin),
):
    task = embed_cards_task.delay()
    return {"task_id": task.id, "status": "queued"}


@router.post("/download/images")
async def download_card_images(
    admin: User = Depends(require_admin),
):
    task = download_card_images_task.delay()
    return {"task_id": task.id, "status": "queued"}


@router.get("/jobs")
async def list_jobs(
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    query = select(BackgroundJob).order_by(BackgroundJob.created_at.desc()).limit(limit)
    if status:
        query = query.where(BackgroundJob.status == status)
    result = await db.execute(query)
    jobs = result.scalars().all()
    return {"jobs": [
        {
            "id": str(j.id),
            "job_type": j.job_type,
            "status": j.status,
            "progress": j.progress,
            "created_at": j.created_at.isoformat() if j.created_at else None,
            "completed_at": j.completed_at.isoformat() if j.completed_at else None,
        }
        for j in jobs
    ]}


@router.get("/analytics")
async def get_analytics(
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    from datetime import datetime, timedelta, timezone
    since = datetime.now(timezone.utc) - timedelta(days=days)

    result = await db.execute(
        select(AnalyticsEvent.event_type, func.count().label("count"))
        .where(AnalyticsEvent.created_at >= since)
        .group_by(AnalyticsEvent.event_type)
        .order_by(func.count().desc())
    )
    event_counts = [{"event_type": r.event_type, "count": r.count} for r in result]

    token_result = await db.execute(
        select(func.sum(AnalyticsEvent.token_count))
        .where(AnalyticsEvent.created_at >= since)
    )
    total_tokens = token_result.scalar() or 0

    return {"event_counts": event_counts, "total_tokens": total_tokens, "days": days}
