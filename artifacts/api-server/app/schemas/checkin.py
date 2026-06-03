from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class CheckInCreate(BaseModel):
    date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    mood_rating: int = Field(..., ge=1, le=5)
    stress_level: int = Field(..., ge=1, le=5)
    sleep_hours: float = Field(..., ge=0, le=24)
    energy_level: Optional[int] = Field(None, ge=1, le=5)
    exercised: bool = False
    socialized: bool = False
    workload_level: Optional[int] = Field(None, ge=1, le=5)
    notes: Optional[str] = None


class CheckInResponse(BaseModel):
    id: int
    user_id: int
    date: str
    mood_rating: int
    stress_level: int
    sleep_hours: float
    energy_level: Optional[int]
    exercised: bool
    socialized: bool
    workload_level: Optional[int]
    notes: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}
