"""Meta scraper service — orchestrates scraping jobs and serves meta data."""
from __future__ import annotations

from sqlalchemy import case, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.models.card import Card
from app.models.meta import MetaDeck, MetaDeckCard, MetaSource, ScrapedDocument
from app.schemas.card import CardOut

logger = get_logger(__name__)

_TIER_ORDER = case({"S": 0, "A": 1, "B": 2, "C": 3}, value=MetaDeck.tier, else_=4)


class MetaScraperService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_popular_decks(
        self,
        format: str = "tcg",
        tier: str | None = None,
        archetype: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        query = (
            select(MetaDeck)
            .options(
                selectinload(MetaDeck.cards)
                .selectinload(MetaDeckCard.card)
                .selectinload(Card.prints)
            )
            .where(MetaDeck.format == format, MetaDeck.has_full_list.is_(True))
        )
        if tier:
            query = query.where(MetaDeck.tier == tier.upper())
        if archetype:
            query = query.where(MetaDeck.archetype.ilike(f"%{archetype}%"))
        query = query.order_by(_TIER_ORDER, MetaDeck.tournament_appearances.desc())

        total_result = await self.db.execute(
            select(MetaDeck).where(MetaDeck.format == format, MetaDeck.has_full_list.is_(True))
        )
        total = len(total_result.scalars().all())

        offset = (page - 1) * page_size
        result = await self.db.execute(query.offset(offset).limit(page_size))
        decks = result.scalars().all()

        out = []
        for deck in decks:
            key_cards = await self._resolve_cards(deck.key_card_ids or [])

            def _card_entry(dc: MetaDeckCard) -> dict | None:
                if not dc.card:
                    return None
                return {
                    "card_id": str(dc.card_id),
                    "zone": dc.zone,
                    "quantity": dc.quantity,
                    "ordering": dc.ordering,
                    "card": CardOut.model_validate(dc.card).model_dump(by_alias=True),
                }

            zone_cards = [_card_entry(dc) for dc in deck.cards if dc.card]
            zone_cards = [e for e in zone_cards if e]

            out.append({
                "id": str(deck.id),
                "name": deck.name,
                "archetype": deck.archetype,
                "format": deck.format,
                "tier": deck.tier,
                "source_name": deck.source_name,
                "source_url": deck.source_url,
                "win_rate": deck.win_rate,
                "tournament_appearances": deck.tournament_appearances,
                "has_full_list": deck.has_full_list,
                "key_cards": [CardOut.model_validate(c).model_dump(by_alias=True) for c in key_cards],
                "main_deck": [e for e in zone_cards if e["zone"] == "main"],
                "extra_deck": [e for e in zone_cards if e["zone"] == "extra"],
                "side_deck": [e for e in zone_cards if e["zone"] == "side"],
                "description": deck.description,
                "scraped_at": deck.scraped_at.isoformat() if deck.scraped_at else None,
            })

        return {
            "decks": out,
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": max(1, (total + page_size - 1) // page_size),
        }

    async def get_popular_cards(self, format: str = "tcg", limit: int = 20) -> list[dict]:
        result = await self.db.execute(
            select(Card)
            .options(selectinload(Card.prints))
            .order_by(Card.popularity_score.desc())
            .limit(limit)
        )
        cards = result.scalars().all()
        return [CardOut.model_validate(c).model_dump(by_alias=True) for c in cards]

    async def get_archetypes(self, format: str = "tcg") -> dict:
        from sqlalchemy import func
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
        return {"trends": [], "format": format, "note": "Trend data populated by scraping jobs"}

    async def trigger_rebuild(self) -> dict:
        from app.worker.tasks.scrape_tasks import scrape_all_sources_task
        task = scrape_all_sources_task.delay()
        return {"task_id": task.id, "status": "queued"}

    async def _resolve_cards(self, card_ids: list) -> list[Card]:
        if not card_ids:
            return []
        result = await self.db.execute(
            select(Card)
            .options(selectinload(Card.prints))
            .where(Card.id.in_(card_ids))
        )
        cards_by_id = {c.id: c for c in result.scalars().all()}
        return [cards_by_id[cid] for cid in card_ids if cid in cards_by_id]
