import uuid
from datetime import datetime
from sqlalchemy import (
    Boolean, Column, Date, DateTime, Enum, ForeignKey,
    Integer, SmallInteger, String, Text, ARRAY, Numeric,
    UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from app.db.session import Base


class Card(Base):
    __tablename__ = "cards"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ygoprodeck_id = Column(Integer, unique=True, index=True)
    konami_id = Column(String)
    name_en = Column(Text, nullable=False)
    name_ja = Column(Text)
    card_type = Column(Enum("monster", "spell", "trap", name="card_type"), nullable=False)
    monster_type = Column(Enum(
        "normal", "effect", "ritual", "fusion", "synchro", "xyz", "link",
        "pendulum", "token", "flip", "spirit", "union", "gemini", "tuner",
        name="monster_type"
    ))
    race = Column(String)
    attribute = Column(Enum(
        "dark", "light", "earth", "water", "fire", "wind", "divine",
        name="card_attribute"
    ))
    level = Column(SmallInteger)
    rank = Column(SmallInteger)
    link_rating = Column(SmallInteger)
    link_markers = Column(ARRAY(String))
    pendulum_scale = Column(SmallInteger)
    atk = Column(Integer)
    def_ = Column("def", Integer)
    effect_text = Column(Text)
    pendulum_text = Column(Text)
    flavor_text = Column(Text)
    archetype = Column(String)
    tcg_ban_status = Column(
        Enum("unlimited", "semi-limited", "limited", "forbidden", name="ban_status"),
        nullable=False,
        default="unlimited",
    )
    ocg_ban_status = Column(
        Enum("unlimited", "semi-limited", "limited", "forbidden", name="ban_status"),
        nullable=False,
        default="unlimited",
    )
    is_extra_deck = Column(Boolean, nullable=False, default=False)
    views = Column(Integer, nullable=False, default=0)
    popularity_score = Column(Numeric(10, 6), nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())

    prints = relationship("CardPrint", back_populates="card", cascade="all, delete-orphan")
    embeddings = relationship("CardEmbedding", back_populates="card", cascade="all, delete-orphan")


class CardPrint(Base):
    __tablename__ = "card_prints"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    card_id = Column(UUID(as_uuid=True), ForeignKey("cards.id", ondelete="CASCADE"), nullable=False)
    set_code = Column(String)
    set_name = Column(String)
    card_number = Column(String)
    rarity = Column(String)
    region = Column(String)
    language = Column(String, default="en")
    release_date = Column(Date)
    image_url = Column(Text)
    image_url_small = Column(Text)
    image_url_cropped = Column(Text)
    official_url = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    card = relationship("Card", back_populates="prints")


class CardEmbedding(Base):
    __tablename__ = "card_embeddings"
    __table_args__ = (UniqueConstraint("card_id", "chunk_type", name="uq_card_embeddings_card_chunk"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    card_id = Column(UUID(as_uuid=True), ForeignKey("cards.id", ondelete="CASCADE"), nullable=False)
    chunk_type = Column(String, nullable=False)
    chunk_text = Column(Text, nullable=False)
    embedding = Column(Vector(768))
    metadata_ = Column("metadata", JSONB, default=dict)
    source = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    card = relationship("Card", back_populates="embeddings")
