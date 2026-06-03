from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.repositories.checkin import CheckInRepository
from app.schemas.checkin import CheckInCreate, CheckInResponse

router = APIRouter(prefix="/checkins", tags=["checkins"])


@router.post("", response_model=CheckInResponse, status_code=201)
def create_checkin(body: CheckInCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    checkin = CheckInRepository.create(db, user_id=current_user.id, data=body)
    return checkin


@router.get("", response_model=List[CheckInResponse])
def list_checkins(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return CheckInRepository.get_all_for_user(db, user_id=current_user.id, limit=limit, offset=offset)


@router.get("/{checkin_id}", response_model=CheckInResponse)
def get_checkin(checkin_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    checkin = CheckInRepository.get_by_id(db, checkin_id=checkin_id, user_id=current_user.id)
    if not checkin:
        raise HTTPException(status_code=404, detail="Check-in not found")
    return checkin
