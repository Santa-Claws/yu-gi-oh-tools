"""Download card images from CDN to local storage and update DB URLs."""
import asyncio
import os
from pathlib import Path

import httpx
from sqlalchemy import select, update

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal
from app.models.card import Card, CardPrint
from app.worker.celery_app import celery_app

logger = get_logger(__name__)

_AI_SERVICE_URL_ENV = "AI_SERVICE_URL"


def _local_url(ygoprodeck_id: int, suffix: str = "") -> str:
    """Return the relative URL path we'll serve locally."""
    return f"/card-images/{ygoprodeck_id}{suffix}.jpg"


async def _download_image(client: httpx.AsyncClient, url: str, dest: Path) -> bool:
    """Download a single image; return True on success."""
    if dest.exists():
        return True
    try:
        resp = await client.get(url, timeout=30)
        resp.raise_for_status()
        dest.write_bytes(resp.content)
        return True
    except Exception as e:
        logger.warning("image_download_failed", url=url, error=str(e))
        return False


async def _run_download():
    settings = get_settings()
    images_dir = Path(settings.card_images_dir)
    images_dir.mkdir(parents=True, exist_ok=True)

    async with AsyncSessionLocal() as db:
        # Load all prints that still have CDN URLs (start with https://)
        result = await db.execute(
            select(CardPrint, Card.ygoprodeck_id)
            .join(Card, Card.id == CardPrint.card_id)
            .where(
                CardPrint.image_url.like("https://%"),
                Card.ygoprodeck_id.isnot(None),
            )
        )
        rows = result.all()

    logger.info("download_images_start", total=len(rows))

    downloaded = 0
    failed = 0

    async with httpx.AsyncClient(follow_redirects=True) as client:
        for i, (print_row, ygo_id) in enumerate(rows):
            updates: dict = {}

            for attr, suffix in [
                ("image_url", ""),
                ("image_url_small", "_small"),
                ("image_url_cropped", "_cropped"),
            ]:
                cdn_url = getattr(print_row, attr)
                if not cdn_url or not cdn_url.startswith("https://"):
                    continue
                dest = images_dir / f"{ygo_id}{suffix}.jpg"
                ok = await _download_image(client, cdn_url, dest)
                if ok:
                    updates[attr] = _local_url(ygo_id, suffix)
                    downloaded += 1
                else:
                    failed += 1

            if updates:
                async with AsyncSessionLocal() as db:
                    await db.execute(
                        update(CardPrint)
                        .where(CardPrint.id == print_row.id)
                        .values(**updates)
                    )
                    await db.commit()

            if i % 100 == 0:
                logger.info(
                    "download_images_progress",
                    done=i,
                    total=len(rows),
                    downloaded=downloaded,
                    failed=failed,
                )

    logger.info("download_images_complete", downloaded=downloaded, failed=failed)
    return {"downloaded": downloaded, "failed": failed}


@celery_app.task(name="app.worker.tasks.download_images_task.download_card_images_task", bind=True)
def download_card_images_task(self):
    return asyncio.run(_run_download())
