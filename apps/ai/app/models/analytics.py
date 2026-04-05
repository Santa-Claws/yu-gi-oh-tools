import uuid
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.db.session import Base


class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    event_type = Column(Text, nullable=False)
    payload = Column(JSONB, default=dict)
    token_count = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SearchLog(Base):
    __tablename__ = "search_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    query_text = Column(Text)
    intent = Column(String)
    result_count = Column(Integer)
    clicked_card_id = Column(UUID(as_uuid=True), ForeignKey("cards.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class BackgroundJob(Base):
    __tablename__ = "background_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_type = Column(
        String,
        Enum("scrape", "import", "index", "embed", name="job_type"),
        nullable=False,
    )
    status = Column(
        String,
        Enum("pending", "running", "completed", "failed", "cancelled", name="job_status"),
        nullable=False,
        default="pending",
    )
    celery_id = Column(String)
    progress = Column(Integer, nullable=False, default=0)
    logs = Column(Text)
    error = Column(Text)
    payload = Column(JSONB, default=dict)
    result = Column(JSONB)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
