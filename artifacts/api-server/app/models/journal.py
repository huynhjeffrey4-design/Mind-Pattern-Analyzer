from datetime import datetime
from typing import Optional
from sqlalchemy import Boolean, Integer, String, Text, DateTime, ForeignKey, Float, func
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class JournalEntry(Base):
    __tablename__ = "journal_entries_v2"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    keywords: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sentiment_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sentiment_label: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    safety_flagged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
