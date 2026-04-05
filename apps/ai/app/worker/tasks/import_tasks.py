"""Card import task — fetches all cards from YGOProDeck API and upserts into DB."""
import asyncio
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal
from app.models.card import Card, CardPrint
from app.worker.celery_app import celery_app

logger = get_logger(__name__)

YGOPRODECK_ALL_CARDS = "{api_url}/cardinfo.php?misc=yes&num=10000&offset=0"

MONSTER_EXTRA_TYPES = {"fusion", "synchro", "xyz", "link"}


def _is_extra_deck(card_data: dict) -> bool:
    frame = card_data.get("frameType", "").lower()
    return any(t in frame for t in MONSTER_EXTRA_TYPES)


def _map_card(data: dict) -> dict:
    frame = data.get("frameType", "").lower()
    card_type = "monster" if "monster" in frame else ("spell" if frame == "spell" else "trap")

    # ban status
    banlist = data.get("banlist_info", {})
    tcg_ban = _normalize_ban(banlist.get("ban_tcg", "Unlimited"))
    ocg_ban = _normalize_ban(banlist.get("ban_ocg", "Unlimited"))

    return {
        "ygoprodeck_id": data["id"],
        "name_en": data.get("name", ""),
        "card_type": card_type,
        "monster_type": _infer_monster_type(data),
        "race": data.get("race"),
        "attribute": (data.get("attribute") or "").lower() or None,
        "level": data.get("level"),
        "rank": data.get("level") if "xyz" in frame else None,
        "link_rating": data.get("linkval"),
        "link_markers": data.get("linkmarkers"),
        "pendulum_scale": data.get("scale"),
        "atk": data.get("atk"),
        "def": data.get("def"),
        "effect_text": data.get("desc"),
        "archetype": data.get("archetype"),
        "tcg_ban_status": tcg_ban,
        "ocg_ban_status": ocg_ban,
        "is_extra_deck": _is_extra_deck(data),
        "updated_at": datetime.now(timezone.utc),
    }


def _infer_monster_type(data: dict) -> str | None:
    frame = data.get("frameType", "").lower()
    if "monster" not in frame:
        return None
    for t in ["fusion", "synchro", "xyz", "link", "ritual", "pendulum"]:
        if t in frame:
            return t
    return "effect" if "effect" in (data.get("desc") or "").lower() else "normal"


def _normalize_ban(status: str) -> str:
    mapping = {
        "Banned": "forbidden",
        "Limited": "limited",
        "Semi-Limited": "semi-limited",
        "Unlimited": "unlimited",
    }
    return mapping.get(status, "unlimited")


def _map_print(card_db_id, card_image: dict, card_set: dict | None = None) -> dict:
    return {
        "card_id": card_db_id,
        "set_code": card_set.get("set_code") if card_set else None,
        "set_name": card_set.get("set_name") if card_set else None,
        "card_number": card_set.get("set_code") if card_set else None,
        "rarity": card_set.get("set_rarity") if card_set else None,
        "region": "TCG",
        "language": "en",
        "image_url": card_image.get("image_url"),
        "image_url_small": card_image.get("image_url_small"),
        "image_url_cropped": card_image.get("image_url_cropped"),
    }


async def _run_import(limit: int | None = None):
    settings = get_settings()
    url = YGOPRODECK_ALL_CARDS.format(api_url=settings.ygoprodeck_api_url)

    logger.info("import_cards_start", url=url)

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()

    cards_data = data.get("data", [])
    if limit:
        cards_data = cards_data[:limit]

    logger.info("import_cards_fetched", count=len(cards_data))

    async with AsyncSessionLocal() as db:
        for i, card_data in enumerate(cards_data):
            try:
                mapped = _map_card(card_data)

                # Upsert card
                stmt = pg_insert(Card).values(**mapped).on_conflict_do_update(
                    index_elements=["ygoprodeck_id"],
                    set_={k: v for k, v in mapped.items() if k != "ygoprodeck_id"},
                ).returning(Card.id)
                result = await db.execute(stmt)
                card_db_id = result.scalar_one()

                # Upsert prints
                images = card_data.get("card_images", [])
                sets = card_data.get("card_sets", [])

                for img in images[:1]:  # primary image only on import
                    for s in sets[:3] or [None]:
                        print_data = _map_print(card_db_id, img, s)
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

        await db.commit()

    logger.info("import_cards_complete", total=len(cards_data))
    return {"imported": len(cards_data)}


@celery_app.task(name="app.worker.tasks.import_tasks.import_cards_task", bind=True)
def import_cards_task(self, limit: int | None = None):
    return asyncio.get_event_loop().run_until_complete(_run_import(limit))
