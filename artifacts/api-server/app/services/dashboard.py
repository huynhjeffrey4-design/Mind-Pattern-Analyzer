from typing import List, Optional
from sqlalchemy.orm import Session
from app.repositories.checkin import CheckInRepository
from app.models.checkin import CheckIn


def _compute_streak(checkins: List[CheckIn]) -> int:
    if not checkins:
        return 0
    from datetime import date, timedelta
    dates = sorted({c.date for c in checkins}, reverse=True)
    today = date.today().isoformat()
    streak = 0
    expected = today
    for d in dates:
        if d == expected:
            streak += 1
            prev = date.fromisoformat(d) - timedelta(days=1)
            expected = prev.isoformat()
        else:
            break
    return streak


def get_summary(db: Session, user_id: int) -> dict:
    checkins = CheckInRepository.get_recent_for_user(db, user_id, limit=200)
    total = len(checkins)
    avg_mood = round(sum(c.mood_rating for c in checkins) / total, 2) if total else None
    avg_stress = round(sum(c.stress_level for c in checkins) / total, 2) if total else None
    avg_sleep = round(sum(c.sleep_hours for c in checkins) / total, 2) if total else None
    streak = _compute_streak(checkins)
    return {
        "total_checkins": total,
        "avg_mood": avg_mood,
        "avg_stress": avg_stress,
        "avg_sleep": avg_sleep,
        "current_streak": streak,
    }


def get_mood_trends(db: Session, user_id: int, days: int = 30) -> List[dict]:
    checkins = CheckInRepository.get_recent_for_user(db, user_id, limit=days)
    return [{"date": c.date, "value": float(c.mood_rating)} for c in reversed(checkins)]


def get_stress_trends(db: Session, user_id: int, days: int = 30) -> List[dict]:
    checkins = CheckInRepository.get_recent_for_user(db, user_id, limit=days)
    return [{"date": c.date, "value": float(c.stress_level)} for c in reversed(checkins)]


def get_sleep_mood(db: Session, user_id: int) -> List[dict]:
    checkins = CheckInRepository.get_recent_for_user(db, user_id, limit=60)
    return [
        {"sleep_hours": c.sleep_hours, "mood_rating": float(c.mood_rating), "date": c.date}
        for c in checkins
    ]
