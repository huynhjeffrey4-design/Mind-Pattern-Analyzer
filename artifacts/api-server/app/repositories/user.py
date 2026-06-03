from typing import Optional
from sqlalchemy.orm import Session
from app.models.user import User


class UserRepository:
    @staticmethod
    def get_by_id(db: Session, user_id: int) -> Optional[User]:
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def get_by_email(db: Session, email: str) -> Optional[User]:
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    def create(db: Session, email: str, hashed_password: str, display_name: Optional[str] = None) -> User:
        user = User(
            email=email,
            hashed_password=hashed_password,
            display_name=display_name,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def update_settings(db: Session, user: User, ai_analysis_enabled: Optional[bool], weekly_summary_enabled: Optional[bool]) -> User:
        if ai_analysis_enabled is not None:
            user.ai_analysis_enabled = ai_analysis_enabled
        if weekly_summary_enabled is not None:
            user.weekly_summary_enabled = weekly_summary_enabled
        db.commit()
        db.refresh(user)
        return user
