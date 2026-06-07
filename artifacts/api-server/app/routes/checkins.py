from datetime import date as date_type
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.repositories.checkin import CheckInRepository
from app.schemas.checkin import CheckInCreate, CheckInUpdate, CheckInResponse

router = APIRouter(prefix="/checkins", tags=["checkins"])


@router.get("/today", response_model=CheckInResponse)
def get_today_checkin(
    date: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    # Use the client-supplied date when available so timezone differences between
    # the browser and the UTC server never cause a mismatch.
    lookup_date = date or date_type.today().isoformat()
    checkin = CheckInRepository.get_by_date(db, user_id=current_user.id, date=lookup_date)
    if not checkin:
        raise HTTPException(status_code=404, detail="No check-in for today yet")
    return checkin


@router.post("", response_model=CheckInResponse, status_code=201)
def create_checkin(body: CheckInCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    existing = CheckInRepository.get_by_date(db, user_id=current_user.id, date=body.date)
    if existing:
        raise HTTPException(
            status_code=409,
            detail="You've already checked in for this date. Edit your existing check-in instead.",
        )
    return CheckInRepository.create(db, user_id=current_user.id, data=body)


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


@router.patch("/{checkin_id}", response_model=CheckInResponse)
def update_checkin(
    checkin_id: int,
    body: CheckInUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    checkin = CheckInRepository.get_by_id(db, checkin_id=checkin_id, user_id=current_user.id)
    if not checkin:
        raise HTTPException(status_code=404, detail="Check-in not found")
    return CheckInRepository.update(db, checkin=checkin, data=body)
