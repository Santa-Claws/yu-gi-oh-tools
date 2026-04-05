from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.deck import (
    DeckCreate, DeckUpdate, DeckOut, DeckDetailOut, DeckCardIn,
    DeckVersionOut, DeckExportRequest,
)
from app.services.deck.service import DeckService

router = APIRouter(prefix="/decks", tags=["decks"])


@router.get("", response_model=list[DeckOut])
async def list_decks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = DeckService(db)
    return await svc.list_for_user(current_user.id)


@router.post("", response_model=DeckDetailOut, status_code=status.HTTP_201_CREATED)
async def create_deck(
    body: DeckCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = DeckService(db)
    return await svc.create(body, user_id=current_user.id)


@router.get("/{deck_id}", response_model=DeckDetailOut)
async def get_deck(
    deck_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = DeckService(db)
    deck = await svc.get(deck_id, user_id=current_user.id)
    if not deck:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deck not found")
    return deck


@router.put("/{deck_id}", response_model=DeckDetailOut)
async def update_deck(
    deck_id: UUID,
    body: DeckUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = DeckService(db)
    deck = await svc.update(deck_id, body, user_id=current_user.id)
    if not deck:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deck not found")
    return deck


@router.delete("/{deck_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_deck(
    deck_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = DeckService(db)
    deleted = await svc.delete(deck_id, user_id=current_user.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deck not found")


@router.post("/{deck_id}/cards", response_model=DeckDetailOut)
async def add_cards_to_deck(
    deck_id: UUID,
    cards: list[DeckCardIn],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = DeckService(db)
    deck = await svc.add_cards(deck_id, cards, user_id=current_user.id)
    if not deck:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deck not found")
    return deck


@router.delete("/{deck_id}/cards/{card_entry_id}", response_model=DeckDetailOut)
async def remove_card_from_deck(
    deck_id: UUID,
    card_entry_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = DeckService(db)
    deck = await svc.remove_card(deck_id, card_entry_id, user_id=current_user.id)
    if not deck:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return deck


@router.post("/{deck_id}/versions", response_model=DeckVersionOut)
async def save_version(
    deck_id: UUID,
    note: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = DeckService(db)
    version = await svc.save_version(deck_id, note=note, user_id=current_user.id)
    if not version:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deck not found")
    return version


@router.get("/{deck_id}/versions", response_model=list[DeckVersionOut])
async def list_versions(
    deck_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = DeckService(db)
    return await svc.list_versions(deck_id, user_id=current_user.id)


@router.get("/{deck_id}/export")
async def export_deck(
    deck_id: UUID,
    format: str = "json",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = DeckService(db)
    return await svc.export(deck_id, format=format, user_id=current_user.id)
