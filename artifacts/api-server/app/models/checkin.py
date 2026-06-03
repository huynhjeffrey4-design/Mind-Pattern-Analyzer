from datetime import datetime
from typing import Optional
from sqlalchemy import Integer, Float, Boolean, String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class CheckIn(Base):
    __tablename__ = "checkins_v2"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    date: Mapped[str] = mapped_column(String(10), nullable=False)
    mood_rating: Mapped[int] = mapped_column(Integer, nullable=False)
    stress_level: Mapped[int] = mapped_column(Integer, nullable=False)
    sleep_hours: Mapped[float] = mapped_column(Float, nullable=False)
    energy_level: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    exercised: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    socialized: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    workload_level: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
