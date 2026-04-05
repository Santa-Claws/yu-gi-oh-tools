"""Scraping tasks — fetch community meta content and store as scraped documents."""
import asyncio
import re
from datetime import datetime, timezone
from uuid import UUID

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import select

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal
from app.models.meta import MetaSource, ScrapedDocument
from app.worker.celery_app import celery_app

logger = get_logger(__name__)


def _clean_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    # Remove script/style
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    # Collapse whitespace
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    return "\n".join(lines)


async def _scrape_source(source: MetaSource) -> int:
    settings = get_settings()
    headers = {"User-Agent": settings.scrape_user_agent}

    if not source.source_url:
        return 0

    try:
        async with httpx.AsyncClient(timeout=30, headers=headers, follow_redirects=True) as client:
            resp = await client.get(source.source_url)
            resp.raise_for_status()
            html = resp.text
    except Exception as e:
        logger.warning("scrape_fetch_failed", source=source.source_name, error=str(e))
        return 0

    cleaned = _clean_text(html)
    if len(cleaned) < 100:
        return 0

    async with AsyncSessionLocal() as db:
        doc = ScrapedDocument(
            source_id=source.id,
            title=source.source_name,
            url=source.source_url,
            raw_text=html[:50000],  # store first 50k chars of raw
            cleaned_text=cleaned[:100000],
            scraped_at=datetime.now(timezone.utc),
        )
        db.add(doc)
        # Update last_scraped_at
        source.last_scraped_at = datetime.now(timezone.utc)
        db.add(source)
        await db.commit()

    logger.info("scrape_source_done", source=source.source_name, chars=len(cleaned))
    return 1


async def _run_scrape(source_id: str | None = None):
    async with AsyncSessionLocal() as db:
        query = select(MetaSource).where(MetaSource.is_active == True)
        if source_id:
            query = query.where(MetaSource.id == source_id)
        result = await db.execute(query)
        sources = list(result.scalars().all())

    logger.info("scrape_all_start", count=len(sources))
    total = 0
    for source in sources:
        total += await _scrape_source(source)

    return {"scraped": total}


@celery_app.task(name="app.worker.tasks.scrape_tasks.scrape_source_task", bind=True)
def scrape_source_task(self, source_id: str | None = None):
    return asyncio.run(_run_scrape(source_id))


@celery_app.task(name="app.worker.tasks.scrape_tasks.scrape_all_sources_task", bind=True)
def scrape_all_sources_task(self):
    return asyncio.run(_run_scrape())
