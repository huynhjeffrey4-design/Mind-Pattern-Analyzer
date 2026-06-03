from typing import List
from sqlalchemy.orm import Session
from app.models.insight import Insight


class InsightRepository:
    @staticmethod
    def create_bulk(db: Session, user_id: int, insights_data: List[dict]) -> List[Insight]:
        db.query(Insight).filter(Insight.user_id == user_id).delete()
        insights = []
        for data in insights_data:
            insight = Insight(
                user_id=user_id,
                insight_type=data["insight_type"],
                title=data["title"],
                description=data["description"],
                confidence=data.get("confidence"),
                suggestion=data.get("suggestion"),
            )
            db.add(insight)
            insights.append(insight)
        db.commit()
        for insight in insights:
            db.refresh(insight)
        return insights

    @staticmethod
    def get_all_for_user(db: Session, user_id: int) -> List[Insight]:
        return (
            db.query(Insight)
            .filter(Insight.user_id == user_id)
            .order_by(Insight.created_at.desc())
            .all()
        )
