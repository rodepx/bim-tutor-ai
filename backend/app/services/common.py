"""Consultas compartidas entre routers y servicios."""
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models


def latest_snapshot(db: Session, project_code: str | None = None) -> models.Snapshot | None:
    q = select(models.Snapshot)
    if project_code:
        q = q.where(models.Snapshot.project_code == project_code)
    return db.scalars(q.order_by(models.Snapshot.created_at.desc(), models.Snapshot.id.desc()).limit(1)).first()


def resolve_snapshot(db: Session, snapshot_id: int | None) -> models.Snapshot:
    """snapshot_id explícito o, si se omite, el más reciente. 404 si no existe."""
    snap = db.get(models.Snapshot, snapshot_id) if snapshot_id is not None else latest_snapshot(db)
    if snap is None:
        raise HTTPException(404, f"Snapshot {snapshot_id} no existe" if snapshot_id is not None else "No hay snapshots")
    return snap


def previous_snapshot(db: Session, snap: models.Snapshot) -> models.Snapshot | None:
    S = models.Snapshot
    q = (
        select(S)
        .where(S.project_code == snap.project_code, S.id != snap.id)
        .where((S.created_at < snap.created_at) | ((S.created_at == snap.created_at) & (S.id < snap.id)))
        .order_by(S.created_at.desc(), S.id.desc())
        .limit(1)
    )
    return db.scalars(q).first()


def unique_elements(snap: models.Snapshot) -> list[models.Element]:
    """Elementos del snapshot deduplicados por guid (primera aparición)."""
    seen: set[str] = set()
    out = []
    for e in snap.elements:
        if e.guid not in seen:
            seen.add(e.guid)
            out.append(e)
    return out


def snapshot_issues(db: Session, snapshot_id: int, status: str | None = "open") -> list[models.Issue]:
    """Issues presentes en el snapshot, filtrados por su estado dentro de ese snapshot."""
    q = (
        select(models.Issue)
        .join(models.SnapshotIssue, models.SnapshotIssue.issue_id == models.Issue.id)
        .where(models.SnapshotIssue.snapshot_id == snapshot_id)
    )
    if status:
        q = q.where(models.SnapshotIssue.status == status)
    return list(db.scalars(q.order_by(models.Issue.id)))


def open_issue_count(db: Session, snapshot_id: int, severity: str | None = None) -> int:
    q = (
        select(func.count())
        .select_from(models.SnapshotIssue)
        .join(models.Issue, models.SnapshotIssue.issue_id == models.Issue.id)
        .where(models.SnapshotIssue.snapshot_id == snapshot_id, models.SnapshotIssue.status == "open")
    )
    if severity:
        q = q.where(models.Issue.severity == severity)
    return db.scalar(q) or 0


def snapshot_out(db: Session, snap: models.Snapshot) -> dict:
    return {
        "id": snap.id,
        "project_code": snap.project_code,
        "file_name": snap.file_name,
        "version_label": snap.version_label,
        "cde_state": snap.cde_state,
        "rules_version": snap.rules_version,
        "author": snap.author,
        "created_at": snap.created_at,
        "element_count": len(unique_elements(snap)),
        "open_issue_count": open_issue_count(db, snap.id),
    }


def element_dict(e: models.Element) -> dict:
    d = {
        "guid": e.guid,
        "element_id": e.element_id,
        "category": e.category,
        "discipline": e.discipline,
        "family_name": e.family_name,
        "type_name": e.type_name,
        "classification_code": e.classification_code,
        "level": e.level,
        "volume_m3": e.volume_m3,
        "area_m2": e.area_m2,
        "length_m": e.length_m,
        "parameters": e.parameters,
    }
    return d
