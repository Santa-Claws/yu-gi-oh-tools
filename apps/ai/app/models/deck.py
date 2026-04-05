import uuid
from sqlalchemy import (
    Column, DateTime, Enum, ForeignKey, Integer, SmallInteger,
    String, Text, ARRAY, func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.session import Base


class Deck(Base):
    __tablename__ = "decks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(Text, nullable=False)
    description = Column(Text)
    format = Column(String, nullable=False, default="tcg")
    visibility = Column(String, nullable=False, default="private")
    archetype = Column(String)
    tags = Column(ARRAY(String))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="decks")
    versions = relationship("DeckVersion", back_populates="deck", cascade="all, delete-orphan")
    cards = relationship("DeckCard", back_populates="deck", cascade="all, delete-orphan")


class DeckVersion(Base):
    __tablename__ = "deck_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deck_id = Column(UUID(as_uuid=True), ForeignKey("decks.id", ondelete="CASCADE"), nullable=False)
    version_number = Column(Integer, nullable=False)
    note = Column(Text)
    deck_snapshot = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    deck = relationship("Deck", back_populates="versions")


class DeckCard(Base):
    __tablename__ = "deck_cards"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deck_id = Column(UUID(as_uuid=True), ForeignKey("decks.id", ondelete="CASCADE"), nullable=False)
    card_id = Column(UUID(as_uuid=True), ForeignKey("cards.id", ondelete="CASCADE"), nullable=False)
    zone = Column(
        Enum("main", "extra", "side", name="deck_zone"),
        nullable=False,
        default="main",
    )
    quantity = Column(SmallInteger, nullable=False, default=1)
    ordering = Column(Integer, nullable=False, default=0)
    notes = Column(Text)

    deck = relationship("Deck", back_populates="cards")
    card = relationship("Card")
