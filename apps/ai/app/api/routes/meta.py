from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.db.session import get_db
from app.models.user import User
from app.services.meta.scraper import MetaScraperService

router = APIRouter(prefix="/meta", tags=["meta"])


@router.get("/popular-decks")
async def popular_decks(
    format: str = Query(default="tcg"),
    archetype: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    svc = MetaScraperService(db)
    return await svc.get_popular_decks(format=format, archetype=archetype, page=page, page_size=page_size)


@router.get("/archetypes")
async def archetypes(
    format: str = Query(default="tcg"),
    db: AsyncSession = Depends(get_db),
):
    svc = MetaScraperService(db)
    return await svc.get_archetypes(format=format)


@router.get("/trends")
async def trends(
    format: str = Query(default="tcg"),
    db: AsyncSession = Depends(get_db),
):
    svc = MetaScraperService(db)
    return await svc.get_trends(format=format)


@router.post("/rebuild")
async def rebuild_meta(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    svc = MetaScraperService(db)
    return await svc.trigger_rebuild()
