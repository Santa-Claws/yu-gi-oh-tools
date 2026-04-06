from uuid import UUID

from sqlalchemy import select, func, and_, or_, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.card import Card, CardPrint, CardEmbedding
from app.models.user import User
from app.schemas.card import CardSearchParams


class CardSearchService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, card_id: UUID) -> Card | None:
        result = await self.db.execute(
            select(Card)
            .options(selectinload(Card.prints))
            .where(Card.id == card_id)
        )
        return result.scalar_one_or_none()

    async def get_by_ygoprodeck_id(self, ygoprodeck_id: int) -> Card | None:
        result = await self.db.execute(
            select(Card)
            .options(selectinload(Card.prints))
            .where(Card.ygoprodeck_id == ygoprodeck_id)
        )
        return result.scalar_one_or_none()

    async def search(self, params: CardSearchParams, user: User | None = None) -> dict:
        query = select(Card).options(selectinload(Card.prints))
        conditions = []

        if params.q:
            # Trigram-based fuzzy search on name, OR semantic match later
            conditions.append(
                or_(
                    Card.name_en.ilike(f"%{params.q}%"),
                    Card.name_ja.ilike(f"%{params.q}%"),
                    Card.effect_text.ilike(f"%{params.q}%"),
                )
            )
        if params.card_type:
            conditions.append(Card.card_type == params.card_type)
        if params.attribute:
            conditions.append(Card.attribute == params.attribute)
        if params.monster_type:
            conditions.append(Card.monster_type == params.monster_type)
        if params.race:
            conditions.append(Card.race.ilike(f"%{params.race}%"))
        if params.archetype:
            conditions.append(Card.archetype.ilike(f"%{params.archetype}%"))
        if params.level_min is not None:
            conditions.append(Card.level >= params.level_min)
        if params.level_max is not None:
            conditions.append(Card.level <= params.level_max)
        if params.atk_min is not None:
            conditions.append(Card.atk >= params.atk_min)
        if params.atk_max is not None:
            conditions.append(Card.atk <= params.atk_max)
        if params.def_min is not None:
            conditions.append(Card.def_ >= params.def_min)
        if params.def_max is not None:
            conditions.append(Card.def_ <= params.def_max)
        if params.tcg_ban_status:
            conditions.append(Card.tcg_ban_status == params.tcg_ban_status)
        if params.ocg_ban_status:
            conditions.append(Card.ocg_ban_status == params.ocg_ban_status)

        if conditions:
            query = query.where(and_(*conditions))

        # Sorting
        if params.sort == "atk":
            query = query.order_by(Card.atk.desc().nullslast())
        elif params.sort == "def":
            query = query.order_by(Card.def_.desc().nullslast())
        elif params.sort == "level":
            query = query.order_by(Card.level.desc().nullslast())
        elif params.sort == "name":
            query = query.order_by(Card.name_en.asc())
        elif params.sort == "popularity":
            query = query.order_by(Card.views.desc())
        else:
            query = query.order_by(Card.name_en.asc())

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Paginate
        offset = (params.page - 1) * params.page_size
        query = query.offset(offset).limit(params.page_size)

        result = await self.db.execute(query)
        cards = result.scalars().all()

        return {
            "cards": cards,
            "total": total,
            "page": params.page,
            "page_size": params.page_size,
            "pages": (total + params.page_size - 1) // params.page_size,
        }

    async def semantic_search(
        self, query: str, limit: int = 20, chunk_type: str = "full"
    ) -> list[tuple[Card, float]]:
        """Embed query with nomic-embed-text and return cards ranked by cosine similarity."""
        from app.services.embed.ollama import OllamaClient

        ollama = OllamaClient()
        query_vec = await ollama.embed(query)

        result = await self.db.execute(
            select(Card, (1 - CardEmbedding.embedding.cosine_distance(query_vec)).label("similarity"))
            .join(CardEmbedding, Card.id == CardEmbedding.card_id)
            .where(CardEmbedding.chunk_type == chunk_type)
            .order_by(CardEmbedding.embedding.cosine_distance(query_vec))
            .limit(limit)
            .options(selectinload(Card.prints))
        )
        return [(row.Card, float(row.similarity)) for row in result]

    async def fuzzy_search_by_name(self, name: str, limit: int = 5) -> list[Card]:
        """Trigram-based fuzzy match for OCR candidate lookup."""
        result = await self.db.execute(
            select(Card)
            .options(selectinload(Card.prints))
            .where(
                or_(
                    text("name_en % :name").bindparams(name=name),
                    Card.name_en.ilike(f"%{name}%"),
                )
            )
            .order_by(text("similarity(name_en, :name) DESC").bindparams(name=name))
            .limit(limit)
        )
        return list(result.scalars().all())
