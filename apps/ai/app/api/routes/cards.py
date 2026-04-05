from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select

from app.api.deps import get_current_user_optional
from app.core.config import get_settings
from app.db.session import get_db
from app.models.card import Card, CardPrint
from app.models.user import User
from app.schemas.card import (
    CardOut, CardSearchParams, CardIdentifyTextRequest, CardIdentifyResponse,
)
from app.services.card.search import CardSearchService
from app.services.card.ygoprodeck import map_card, map_print
from app.services.identify.pipeline import IdentificationPipeline

router = APIRouter(prefix="/cards", tags=["cards"])


@router.get("", response_model=dict)
async def search_cards(
    q: str | None = Query(default=None),
    card_type: str | None = Query(default=None),
    attribute: str | None = Query(default=None),
    monster_type: str | None = Query(default=None),
    race: str | None = Query(default=None),
    archetype: str | None = Query(default=None),
    level_min: int | None = Query(default=None),
    level_max: int | None = Query(default=None),
    atk_min: int | None = Query(default=None),
    atk_max: int | None = Query(default=None),
    def_min: int | None = Query(default=None),
    def_max: int | None = Query(default=None),
    tcg_ban_status: str | None = Query(default=None),
    ocg_ban_status: str | None = Query(default=None),
    set_code: str | None = Query(default=None),
    rarity: str | None = Query(default=None),
    sort: str = Query(default="relevance"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=24, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    params = CardSearchParams(
        q=q, card_type=card_type, attribute=attribute,
        monster_type=monster_type, race=race, archetype=archetype,
        level_min=level_min, level_max=level_max,
        atk_min=atk_min, atk_max=atk_max,
        def_min=def_min, def_max=def_max,
        tcg_ban_status=tcg_ban_status, ocg_ban_status=ocg_ban_status,
        set_code=set_code, rarity=rarity,
        sort=sort, page=page, page_size=page_size,
    )
    svc = CardSearchService(db)
    return await svc.search(params, user=current_user)


@router.get("/{card_id}", response_model=CardOut)
async def get_card(card_id: UUID, db: AsyncSession = Depends(get_db)):
    svc = CardSearchService(db)
    card = await svc.get_by_id(card_id)
    if not card:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
    return card


@router.get("/by-id/{ygoprodeck_id}", response_model=CardOut)
async def get_card_by_ygoprodeck_id(
    ygoprodeck_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Look up a card by YGOProDeck ID. Falls back to upstream API and auto-imports if not found locally."""
    svc = CardSearchService(db)
    card = await svc.get_by_ygoprodeck_id(ygoprodeck_id)
    if card:
        return card

    settings = get_settings()
    url = f"{settings.ygoprodeck_api_url}/cardinfo.php?id={ygoprodeck_id}&misc=yes"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url)
            if resp.status_code == 400:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
            resp.raise_for_status()
            upstream_data = resp.json().get("data", [])
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Upstream error: {exc}")

    if not upstream_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")

    card_data = upstream_data[0]
    mapped = map_card(card_data)

    stmt = pg_insert(Card).values(**mapped).on_conflict_do_update(
        index_elements=["ygoprodeck_id"],
        set_={k: v for k, v in mapped.items() if k != "ygoprodeck_id"},
    ).returning(Card.id)
    result = await db.execute(stmt)
    card_db_id = result.scalar_one()

    for img in card_data.get("card_images", [])[:1]:
        for s in card_data.get("card_sets", [])[:3] or [None]:
            print_data = map_print(card_db_id, img, s)
            await db.execute(pg_insert(CardPrint).values(**print_data).on_conflict_do_nothing())

    await db.commit()

    result = await db.execute(
        select(Card).options(selectinload(Card.prints)).where(Card.id == card_db_id)
    )
    return result.scalar_one()


@router.post("/identify/image", response_model=CardIdentifyResponse)
async def identify_card_image(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    pipeline = IdentificationPipeline(db)
    image_bytes = await file.read()
    return await pipeline.identify_from_image(image_bytes, filename=file.filename)


@router.post("/identify/text", response_model=CardIdentifyResponse)
async def identify_card_text(
    body: CardIdentifyTextRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    pipeline = IdentificationPipeline(db)
    return await pipeline.identify_from_text(body.text, language=body.language)
