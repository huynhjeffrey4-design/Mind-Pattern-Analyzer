from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.services import dashboard as dashboard_service
from app.schemas.dashboard import DashboardSummary, MoodTrendResponse, StressTrendResponse, SleepMoodResponse, TrendPoint, SleepMoodPoint

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def summary(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return dashboard_service.get_summary(db, current_user.id)


@router.get("/mood-trends", response_model=MoodTrendResponse)
def mood_trends(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    trends = dashboard_service.get_mood_trends(db, current_user.id)
    return MoodTrendResponse(trends=[TrendPoint(**t) for t in trends])


@router.get("/stress-trends", response_model=StressTrendResponse)
def stress_trends(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    trends = dashboard_service.get_stress_trends(db, current_user.id)
    return StressTrendResponse(trends=[TrendPoint(**t) for t in trends])


@router.get("/sleep-mood", response_model=SleepMoodResponse)
def sleep_mood(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    data = dashboard_service.get_sleep_mood(db, current_user.id)
    return SleepMoodResponse(data=[SleepMoodPoint(**d) for d in data])
