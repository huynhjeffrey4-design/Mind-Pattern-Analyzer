from sqlalchemy.orm import Session
from app.models.safety_event import SafetyEvent


class SafetyEventRepository:
    @staticmethod
    def create(db: Session, user_id: int, source_type: str, source_id: int, matched_keywords: str) -> SafetyEvent:
        event = SafetyEvent(
            user_id=user_id,
            source_type=source_type,
            source_id=source_id,
            matched_keywords=matched_keywords,
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        return event
