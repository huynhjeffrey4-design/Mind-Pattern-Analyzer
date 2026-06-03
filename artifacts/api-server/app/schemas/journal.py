from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class JournalCreate(BaseModel):
    title: Optional[str] = None
    content: str


class JournalResponse(BaseModel):
    id: int
    user_id: int
    title: Optional[str]
    content: str
    keywords: Optional[List[str]]
    sentiment_score: Optional[float]
    sentiment_label: Optional[str]
    safety_flagged: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_with_keywords(cls, entry) -> "JournalResponse":
        keywords_list = None
        if entry.keywords:
            keywords_list = [k.strip() for k in entry.keywords.split(",") if k.strip()]
        return cls(
            id=entry.id,
            user_id=entry.user_id,
            title=entry.title,
            content=entry.content,
            keywords=keywords_list,
            sentiment_score=entry.sentiment_score,
            sentiment_label=entry.sentiment_label,
            safety_flagged=bool(entry.safety_flagged),
            created_at=entry.created_at,
            updated_at=entry.updated_at,
        )
