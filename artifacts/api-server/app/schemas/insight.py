from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class InsightResponse(BaseModel):
    id: int
    user_id: int
    insight_type: str
    title: str
    description: str
    confidence: Optional[float]
    suggestion: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class InsightGenerateResponse(BaseModel):
    insights: List[InsightResponse]
    generated_count: int
