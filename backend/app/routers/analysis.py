from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.db import get_db
from app.services.budget import compute_budget, compute_diff
from app.services.common import resolve_snapshot
from app.services.stats import compute_stats

router = APIRouter(tags=["analisis"])
_404 = {404: {"model": schemas.Error}}


@router.get("/stats", response_model=schemas.Stats, responses=_404)
def get_stats(snapshot_id: int | None = None, db: Session = Depends(get_db)):
    return compute_stats(db, resolve_snapshot(db, snapshot_id))


@router.get("/budget", response_model=schemas.Budget, responses=_404)
def get_budget(snapshot_id: int | None = None, db: Session = Depends(get_db)):
    return compute_budget(db, resolve_snapshot(db, snapshot_id))


@router.get("/budget/diff", response_model=schemas.BudgetDiff, responses=_404)
def get_budget_diff(from_snapshot_id: int, to_snapshot_id: int, db: Session = Depends(get_db)):
    a, b = db.get(models.Snapshot, from_snapshot_id), db.get(models.Snapshot, to_snapshot_id)
    if a is None or b is None:
        missing = from_snapshot_id if a is None else to_snapshot_id
        raise HTTPException(404, f"Snapshot {missing} no existe")
    return compute_diff(db, a, b)
