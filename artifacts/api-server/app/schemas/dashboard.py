from typing import List, Optional
from pydantic import BaseModel


class DashboardSummary(BaseModel):
    total_checkins: int
    avg_mood: Optional[float]
    avg_stress: Optional[float]
    avg_sleep: Optional[float]
    current_streak: int


class TrendPoint(BaseModel):
    date: str
    value: float


class MoodTrendResponse(BaseModel):
    trends: List[TrendPoint]


class StressTrendResponse(BaseModel):
    trends: List[TrendPoint]


class SleepMoodPoint(BaseModel):
    sleep_hours: float
    mood_rating: float
    date: str


class SleepMoodResponse(BaseModel):
    data: List[SleepMoodPoint]
