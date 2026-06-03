from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.checkin import CheckIn
from app.schemas.checkin import CheckInCreate


class CheckInRepository:
    @staticmethod
    def create(db: Session, user_id: int, data: CheckInCreate) -> CheckIn:
        checkin = CheckIn(
            user_id=user_id,
            date=data.date,
            mood_rating=data.mood_rating,
            stress_level=data.stress_level,
            sleep_hours=data.sleep_hours,
            energy_level=data.energy_level,
            exercised=data.exercised,
            socialized=data.socialized,
            workload_level=data.workload_level,
            notes=data.notes,
        )
        db.add(checkin)
        db.commit()
        db.refresh(checkin)
        return checkin

    @staticmethod
    def get_all_for_user(db: Session, user_id: int, limit: int = 50, offset: int = 0) -> List[CheckIn]:
        return (
            db.query(CheckIn)
            .filter(CheckIn.user_id == user_id)
            .order_by(CheckIn.date.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )

    @staticmethod
    def get_by_id(db: Session, checkin_id: int, user_id: int) -> Optional[CheckIn]:
        return (
            db.query(CheckIn)
            .filter(CheckIn.id == checkin_id, CheckIn.user_id == user_id)
            .first()
        )

    @staticmethod
    def get_recent_for_user(db: Session, user_id: int, limit: int = 60) -> List[CheckIn]:
        return (
            db.query(CheckIn)
            .filter(CheckIn.user_id == user_id)
            .order_by(CheckIn.date.desc())
            .limit(limit)
            .all()
        )
