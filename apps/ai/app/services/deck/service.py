from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status
from fastapi.responses import JSONResponse, PlainTextResponse

from app.models.card import Card
from app.models.deck import Deck, DeckCard, DeckVersion
from app.schemas.deck import DeckCreate, DeckUpdate, DeckCardIn


class DeckService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_owned(self, deck_id: UUID, user_id: UUID) -> Deck | None:
        result = await self.db.execute(
            select(Deck)
            .options(
                selectinload(Deck.cards)
                .selectinload(DeckCard.card)
                .selectinload(Card.prints)
            )
            .where(Deck.id == deck_id, Deck.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id: UUID) -> list[Deck]:
        result = await self.db.execute(
            select(Deck)
            .options(selectinload(Deck.cards))
            .where(Deck.user_id == user_id)
            .order_by(Deck.updated_at.desc())
        )
        decks = list(result.scalars().all())
        # Attach zone counts
        for deck in decks:
            _set_zone_counts(deck)
        return decks

    async def create(self, data: DeckCreate, user_id: UUID) -> Deck:
        deck = Deck(
            user_id=user_id,
            name=data.name,
            description=data.description,
            format=data.format,
            visibility=data.visibility,
            archetype=data.archetype,
            tags=data.tags or [],
        )
        self.db.add(deck)
        await self.db.commit()
        await self.db.refresh(deck, ["cards"])
        _set_zone_counts(deck)
        return deck

    async def get(self, deck_id: UUID, user_id: UUID) -> Deck | None:
        deck = await self._get_owned(deck_id, user_id)
        if deck:
            _set_zone_counts(deck)
        return deck

    async def update(self, deck_id: UUID, data: DeckUpdate, user_id: UUID) -> Deck | None:
        deck = await self._get_owned(deck_id, user_id)
        if not deck:
            return None
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(deck, field, value)
        await self.db.commit()
        await self.db.refresh(deck, ["cards"])
        _set_zone_counts(deck)
        return deck

    async def delete(self, deck_id: UUID, user_id: UUID) -> bool:
        deck = await self._get_owned(deck_id, user_id)
        if not deck:
            return False
        await self.db.delete(deck)
        await self.db.commit()
        return True

    async def add_cards(self, deck_id: UUID, cards: list[DeckCardIn], user_id: UUID) -> Deck | None:
        deck = await self._get_owned(deck_id, user_id)
        if not deck:
            return None
        for entry in cards:
            # Verify card exists
            card_result = await self.db.execute(select(Card).where(Card.id == entry.card_id))
            if not card_result.scalar_one_or_none():
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                    detail=f"Card {entry.card_id} not found")
            dc = DeckCard(
                deck_id=deck_id,
                card_id=entry.card_id,
                zone=entry.zone,
                quantity=entry.quantity,
                ordering=entry.ordering,
                notes=entry.notes,
            )
            self.db.add(dc)
        await self.db.commit()
        await self.db.refresh(deck, ["cards"])
        _set_zone_counts(deck)
        return deck

    async def remove_card(self, deck_id: UUID, card_entry_id: UUID, user_id: UUID) -> Deck | None:
        deck = await self._get_owned(deck_id, user_id)
        if not deck:
            return None
        result = await self.db.execute(
            select(DeckCard).where(DeckCard.id == card_entry_id, DeckCard.deck_id == deck_id)
        )
        entry = result.scalar_one_or_none()
        if entry:
            await self.db.delete(entry)
            await self.db.commit()
        await self.db.refresh(deck, ["cards"])
        _set_zone_counts(deck)
        return deck

    async def save_version(self, deck_id: UUID, note: str | None, user_id: UUID) -> DeckVersion | None:
        deck = await self._get_owned(deck_id, user_id)
        if not deck:
            return None

        # Get current version number
        count_result = await self.db.execute(
            select(func.count()).where(DeckVersion.deck_id == deck_id)
        )
        version_number = (count_result.scalar() or 0) + 1

        snapshot = _build_snapshot(deck)
        version = DeckVersion(
            deck_id=deck_id,
            version_number=version_number,
            note=note,
            deck_snapshot=snapshot,
        )
        self.db.add(version)
        await self.db.commit()
        await self.db.refresh(version)
        return version

    async def list_versions(self, deck_id: UUID, user_id: UUID) -> list[DeckVersion]:
        deck = await self._get_owned(deck_id, user_id)
        if not deck:
            return []
        result = await self.db.execute(
            select(DeckVersion)
            .where(DeckVersion.deck_id == deck_id)
            .order_by(DeckVersion.version_number.desc())
        )
        return list(result.scalars().all())

    async def export(self, deck_id: UUID, format: str, user_id: UUID):
        deck = await self._get_owned(deck_id, user_id)
        if not deck:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deck not found")

        if format == "json":
            return JSONResponse(content=_build_snapshot(deck))

        if format == "text":
            lines = [f"# {deck.name}", f"# Format: {deck.format}", ""]
            zones = {"Main Deck": "main", "Extra Deck": "extra", "Side Deck": "side"}
            for label, zone in zones.items():
                zone_cards = [c for c in deck.cards if c.zone == zone]
                if zone_cards:
                    lines.append(f"[{label}]")
                    for dc in zone_cards:
                        lines.append(f"{dc.quantity}x {dc.card_id}")
                    lines.append("")
            return PlainTextResponse("\n".join(lines))

        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Unknown export format: {format}")


def _set_zone_counts(deck: Deck) -> None:
    deck.main_count = sum(c.quantity for c in deck.cards if c.zone == "main")
    deck.extra_count = sum(c.quantity for c in deck.cards if c.zone == "extra")
    deck.side_count = sum(c.quantity for c in deck.cards if c.zone == "side")


def _build_snapshot(deck: Deck) -> dict:
    return {
        "id": str(deck.id),
        "name": deck.name,
        "description": deck.description,
        "format": deck.format,
        "archetype": deck.archetype,
        "tags": deck.tags or [],
        "cards": [
            {
                "card_id": str(dc.card_id),
                "zone": dc.zone,
                "quantity": dc.quantity,
                "ordering": dc.ordering,
            }
            for dc in deck.cards
        ],
    }
