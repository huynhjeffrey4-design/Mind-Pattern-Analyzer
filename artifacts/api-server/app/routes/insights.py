from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.repositories.insight import InsightRepository
from app.services.insights import generate_insights
from app.schemas.insight import InsightResponse, InsightGenerateResponse

router = APIRouter(prefix="/insights", tags=["insights"])


@router.post("/generate", response_model=InsightGenerateResponse)
def generate(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    insights_data = generate_insights(db, current_user.id)
    insights = InsightRepository.get_all_for_user(db, current_user.id)
    return InsightGenerateResponse(
        insights=[InsightResponse.model_validate(i) for i in insights],
        generated_count=len(insights_data),
    )


@router.get("", response_model=List[InsightResponse])
def list_insights(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    insights = InsightRepository.get_all_for_user(db, current_user.id)
    return insights
