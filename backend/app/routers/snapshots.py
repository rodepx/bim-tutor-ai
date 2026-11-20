from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models, schemas
from app.db import get_db
from app.services.common import element_dict, open_issue_count, snapshot_out
from app.services.snapshots import ingest_snapshot

router = APIRouter(prefix="/snapshots", tags=["modelo"])

GATED_STATES = {"SHARED", "PUBLISHED"}


def _get(db: Session, snapshot_id: int) -> models.Snapshot:
    snap = db.get(models.Snapshot, snapshot_id)
    if snap is None:
        raise HTTPException(404, f"Snapshot {snapshot_id} no existe")
    return snap


@router.post("", response_model=schemas.Snapshot, status_code=201)
def create_snapshot(payload: schemas.SnapshotCreate, db: Session = Depends(get_db)):
    return snapshot_out(db, ingest_snapshot(db, payload))


@router.get("", response_model=list[schemas.Snapshot])
def list_snapshots(project_code: str | None = None, db: Session = Depends(get_db)):
    q = select(models.Snapshot)
    if project_code:
        q = q.where(models.Snapshot.project_code == project_code)
    snaps = db.scalars(q.order_by(models.Snapshot.created_at.desc(), models.Snapshot.id.desc()))
    return [snapshot_out(db, s) for s in snaps]


@router.get("/{snapshot_id}", response_model=schemas.SnapshotDetail)
def get_snapshot(snapshot_id: int, db: Session = Depends(get_db)):
    snap = _get(db, snapshot_id)
    return {**snapshot_out(db, snap), "elements": [element_dict(e) for e in snap.elements]}


@router.patch("/{snapshot_id}/cde-state", response_model=schemas.Snapshot,
              responses={404: {"model": schemas.Error}, 409: {"model": schemas.Error}})
def set_cde_state(snapshot_id: int, body: schemas.CdeStateUpdate, db: Session = Depends(get_db)):
    snap = _get(db, snapshot_id)
    if body.cde_state in GATED_STATES:
        errors = open_issue_count(db, snap.id, "error")
        if errors:
            raise HTTPException(
                409, f"No se puede pasar a {body.cde_state}: hay {errors} issue(s) de severidad error abiertos (BEP §7)"
            )
    snap.cde_state = body.cde_state
    db.commit()
    return snapshot_out(db, snap)
