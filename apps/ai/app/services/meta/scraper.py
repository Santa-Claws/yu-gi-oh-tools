"""Meta scraper service — orchestrates scraping jobs and serves meta data."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.meta import MetaSource, ScrapedDocument

logger = get_logger(__name__)


class MetaScraperService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_popular_decks(
        self,
        format: str = "tcg",
        archetype: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        query = (
            select(ScrapedDocument)
            .join(MetaSource, MetaSource.id == ScrapedDocument.source_id)
            .where(MetaSource.source_type.in_(["tournament_results", "community_deck"]))
            .order_by(ScrapedDocument.scraped_at.desc())
        )
        result = await self.db.execute(query.limit(page_size).offset((page - 1) * page_size))
        docs = list(result.scalars().all())
        return {
            "decks": [
                {
                    "id": str(d.id),
                    "title": d.title,
                    "url": d.url,
                    "scraped_at": d.scraped_at.isoformat() if d.scraped_at else None,
                }
                for d in docs
            ],
            "page": page,
            "page_size": page_size,
        }

    async def get_archetypes(self, format: str = "tcg") -> dict:
        from sqlalchemy import func
        from app.models.card import Card

        result = await self.db.execute(
            select(Card.archetype, func.count().label("count"))
            .where(Card.archetype.isnot(None))
            .group_by(Card.archetype)
            .order_by(func.count().desc())
            .limit(100)
        )
        rows = result.all()
        return {"archetypes": [{"name": r.archetype, "card_count": r.count} for r in rows]}

    async def get_trends(self, format: str = "tcg") -> dict:
        # Placeholder — real implementation will analyze scraped documents
        return {"trends": [], "format": format, "note": "Trend data populated by scraping jobs"}

    async def trigger_rebuild(self) -> dict:
        from app.worker.tasks.scrape_tasks import scrape_all_sources_task
        task = scrape_all_sources_task.delay()
        return {"task_id": task.id, "status": "queued"}
