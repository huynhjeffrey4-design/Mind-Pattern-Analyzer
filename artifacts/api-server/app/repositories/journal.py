from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.journal import JournalEntry


class JournalRepository:
    @staticmethod
    def create(
        db: Session,
        user_id: int,
        title: Optional[str],
        content: str,
        keywords: Optional[str],
        sentiment_score: Optional[float],
        sentiment_label: Optional[str],
        safety_flagged: bool,
    ) -> JournalEntry:
        entry = JournalEntry(
            user_id=user_id,
            title=title,
            content=content,
            keywords=keywords,
            sentiment_score=sentiment_score,
            sentiment_label=sentiment_label,
            safety_flagged=safety_flagged,
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry

    @staticmethod
    def get_all_for_user(db: Session, user_id: int, limit: int = 50, offset: int = 0) -> List[JournalEntry]:
        return (
            db.query(JournalEntry)
            .filter(JournalEntry.user_id == user_id)
            .order_by(JournalEntry.created_at.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )

    @staticmethod
    def get_by_id(db: Session, entry_id: int, user_id: int) -> Optional[JournalEntry]:
        return (
            db.query(JournalEntry)
            .filter(JournalEntry.id == entry_id, JournalEntry.user_id == user_id)
            .first()
        )

    @staticmethod
    def get_recent_for_user(db: Session, user_id: int, limit: int = 30) -> List[JournalEntry]:
        return (
            db.query(JournalEntry)
            .filter(JournalEntry.user_id == user_id)
            .order_by(JournalEntry.created_at.desc())
            .limit(limit)
            .all()
        )
