import uuid
from sqlalchemy import (
    Boolean, Column, DateTime, Enum, ForeignKey, Integer,
    Numeric, String, Text, func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from app.db.session import Base


class MetaSource(Base):
    __tablename__ = "meta_sources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_type = Column(Enum(
        "official_api", "official_site", "tournament_results", "meta_site",
        "forum", "reddit", "community_deck",
        name="source_type",
    ), nullable=False)
    source_name = Column(Text, nullable=False)
    source_url = Column(Text)
    is_active = Column(Boolean, nullable=False, default=True)
    last_scraped_at = Column(DateTime(timezone=True))
    reliability_score = Column(Numeric(3, 2), nullable=False, default=0.5)
    config = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    documents = relationship("ScrapedDocument", back_populates="source", cascade="all, delete-orphan")


class ScrapedDocument(Base):
    __tablename__ = "scraped_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), ForeignKey("meta_sources.id", ondelete="CASCADE"), nullable=False)
    title = Column(Text)
    url = Column(Text)
    raw_text = Column(Text)
    cleaned_text = Column(Text)
    published_at = Column(DateTime(timezone=True))
    scraped_at = Column(DateTime(timezone=True), server_default=func.now())
    chunk_count = Column(Integer, nullable=False, default=0)
    metadata_ = Column("metadata", JSONB, default=dict)

    source = relationship("MetaSource", back_populates="documents")
    embeddings = relationship("DocumentEmbedding", back_populates="document", cascade="all, delete-orphan")


class DocumentEmbedding(Base):
    __tablename__ = "document_embeddings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    doc_id = Column(UUID(as_uuid=True), ForeignKey("scraped_documents.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    chunk_text = Column(Text, nullable=False)
    embedding = Column(Vector(768))
    metadata_ = Column("metadata", JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    document = relationship("ScrapedDocument", back_populates="embeddings")
