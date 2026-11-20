from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models, schemas
from app.db import get_db

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("", response_model=schemas.Feedback, status_code=201)
def create_feedback(body: schemas.FeedbackCreate, db: Session = Depends(get_db)):
    fb = models.Feedback(**body.model_dump())
    db.add(fb)
    db.commit()
    db.refresh(fb)
    return fb


@router.get("", response_model=list[schemas.Feedback])
def list_feedback(rule_id: str | None = None, element_guid: str | None = None, db: Session = Depends(get_db)):
    q = select(models.Feedback)
    if rule_id:
        q = q.where(models.Feedback.rule_id == rule_id)
    if element_guid:
        q = q.where(models.Feedback.element_guid == element_guid)
    return list(db.scalars(q.order_by(models.Feedback.created_at, models.Feedback.id)))
