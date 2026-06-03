from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.repositories.user import UserRepository
from app.schemas.user import UserSettingsUpdate, UserSettingsResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me/settings", response_model=UserSettingsResponse)
def get_settings(current_user=Depends(get_current_user)):
    return current_user


@router.put("/me/settings", response_model=UserSettingsResponse)
def update_settings(
    body: UserSettingsUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    updated = UserRepository.update_settings(
        db,
        user=current_user,
        ai_analysis_enabled=body.ai_analysis_enabled,
        weekly_summary_enabled=body.weekly_summary_enabled,
    )
    return updated
