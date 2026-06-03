from datetime import datetime
from sqlalchemy import Integer, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class SafetyEvent(Base):
    __tablename__ = "safety_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(Text, nullable=False)
    source_id: Mapped[int] = mapped_column(Integer, nullable=False)
    matched_keywords: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
