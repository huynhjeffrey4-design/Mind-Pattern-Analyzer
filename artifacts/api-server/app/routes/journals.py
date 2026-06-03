from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.repositories.journal import JournalRepository
from app.repositories.safety_event import SafetyEventRepository
from app.schemas.journal import JournalCreate, JournalResponse
from app.services.nlp import analyze_text
from app.services.safety import detect_safety_keywords

router = APIRouter(prefix="/journals", tags=["journals"])


@router.post("", response_model=JournalResponse, status_code=201)
def create_journal(body: JournalCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    nlp = analyze_text(body.content)
    flagged, matched_keywords = detect_safety_keywords(body.content)

    keywords_str = ", ".join(nlp["keywords"]) if nlp["keywords"] else None

    entry = JournalRepository.create(
        db,
        user_id=current_user.id,
        title=body.title,
        content=body.content,
        keywords=keywords_str,
        sentiment_score=nlp["sentiment_score"],
        sentiment_label=nlp["sentiment_label"],
        safety_flagged=flagged,
    )

    if flagged:
        SafetyEventRepository.create(
            db,
            user_id=current_user.id,
            source_type="journal",
            source_id=entry.id,
            matched_keywords=", ".join(matched_keywords),
        )

    return JournalResponse.from_orm_with_keywords(entry)


@router.get("", response_model=List[JournalResponse])
def list_journals(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    entries = JournalRepository.get_all_for_user(db, user_id=current_user.id, limit=limit, offset=offset)
    return [JournalResponse.from_orm_with_keywords(e) for e in entries]


@router.get("/{journal_id}", response_model=JournalResponse)
def get_journal(journal_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    entry = JournalRepository.get_by_id(db, entry_id=journal_id, user_id=current_user.id)
    if not entry:
        raise HTTPException(status_code=404, detail="Journal entry not found")
    return JournalResponse.from_orm_with_keywords(entry)
