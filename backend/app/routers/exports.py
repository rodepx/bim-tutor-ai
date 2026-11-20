import re

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.db import get_db
from app.services.common import resolve_snapshot
from app.services.exports import build_4d_csv, build_bcf, build_cobie

router = APIRouter(prefix="/export", tags=["exportes"])

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _attachment(name: str) -> dict:
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", name)
    return {"Content-Disposition": f'attachment; filename="{safe}"'}


@router.get("/bcf", response_class=Response)
def export_bcf(snapshot_id: int | None = None, db: Session = Depends(get_db)):
    snap = resolve_snapshot(db, snapshot_id)
    name = f"{snap.file_name}_{snap.version_label}.bcfzip"
    return Response(build_bcf(db, snap), media_type="application/octet-stream", headers=_attachment(name))


@router.get("/4d.csv", response_class=Response)
def export_4d(snapshot_id: int | None = None, db: Session = Depends(get_db)):
    snap = resolve_snapshot(db, snapshot_id)
    name = f"{snap.file_name}_{snap.version_label}_4d.csv"
    return Response(build_4d_csv(snap), media_type="text/csv; charset=utf-8", headers=_attachment(name))


@router.get("/cobie.xlsx", response_class=Response)
def export_cobie(snapshot_id: int | None = None, db: Session = Depends(get_db)):
    snap = resolve_snapshot(db, snapshot_id)
    name = f"{snap.file_name}_{snap.version_label}_cobie.xlsx"
    return Response(build_cobie(snap), media_type=XLSX, headers=_attachment(name))
