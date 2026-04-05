"""Card import task — fetches all cards from YGOProDeck API and upserts into DB."""
import asyncio

import httpx
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal
from app.models.card import Card, CardPrint
from app.services.card.ygoprodeck import map_card, map_print
from app.worker.celery_app import celery_app

logger = get_logger(__name__)

YGOPRODECK_CARDS_URL = "{api_url}/cardinfo.php?misc=yes&num={num}&offset={offset}"
PAGE_SIZE = 5000


async def _run_import(limit: int | None = None):
    settings = get_settings()
    all_cards: list = []
    offset = 0

    async with httpx.AsyncClient(timeout=120) as client:
        while True:
            url = YGOPRODECK_CARDS_URL.format(
                api_url=settings.ygoprodeck_api_url,
                num=PAGE_SIZE,
                offset=offset,
            )
            logger.info("import_cards_fetch", offset=offset)
            resp = await client.get(url)
            resp.raise_for_status()
            page = resp.json().get("data", [])
            all_cards.extend(page)
            if len(page) < PAGE_SIZE:
                break
            offset += PAGE_SIZE

    if limit:
        all_cards = all_cards[:limit]

    cards_data = all_cards
    logger.info("import_cards_fetched", count=len(cards_data))

    async with AsyncSessionLocal() as db:
        for i, card_data in enumerate(cards_data):
            try:
                mapped = map_card(card_data)

                stmt = pg_insert(Card).values(**mapped).on_conflict_do_update(
                    index_elements=["ygoprodeck_id"],
                    set_={k: v for k, v in mapped.items() if k != "ygoprodeck_id"},
                ).returning(Card.id)
                result = await db.execute(stmt)
                card_db_id = result.scalar_one()

                images = card_data.get("card_images", [])
                sets = card_data.get("card_sets", [])

                for img in images[:1]:
                    for s in sets[:3] or [None]:
                        print_data = map_print(card_db_id, img, s)
                        await db.execute(
                            pg_insert(CardPrint)
                            .values(**print_data)
                            .on_conflict_do_nothing()
                        )

                if i % 500 == 0:
                    await db.commit()
                    logger.info("import_cards_progress", done=i, total=len(cards_data))

            except Exception as e:
                logger.error("import_card_failed", card_id=card_data.get("id"), error=str(e))
                await db.rollback()

        await db.commit()

    logger.info("import_cards_complete", total=len(cards_data))
    return {"imported": len(cards_data)}


@celery_app.task(name="app.worker.tasks.import_tasks.import_cards_task", bind=True)
def import_cards_task(self, limit: int | None = None):
    return asyncio.run(_run_import(limit))
