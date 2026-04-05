from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_optional
from app.db.session import get_db
from app.models.user import User
from app.schemas.recommend import (
    RecommendCardsRequest, RecommendCardsResponse,
    RecommendDeckRequest, MetaRecommendRequest, ExplainRequest,
)
from app.services.recommend.engine import RecommendationEngine

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.post("/cards", response_model=RecommendCardsResponse)
async def recommend_cards(
    body: RecommendCardsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    engine = RecommendationEngine(db)
    return await engine.recommend_cards(body)


@router.post("/deck", response_model=RecommendCardsResponse)
async def recommend_deck(
    body: RecommendDeckRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    engine = RecommendationEngine(db)
    return await engine.recommend_deck(body)


@router.post("/meta", response_model=dict)
async def meta_recommendations(
    body: MetaRecommendRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    engine = RecommendationEngine(db)
    return await engine.meta_overview(body)


@router.post("/explain", response_model=dict)
async def explain_card(
    body: ExplainRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    engine = RecommendationEngine(db)
    return await engine.explain_card(body)
