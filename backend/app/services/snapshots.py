"""Ingesta de snapshots y ciclo de vida de issues."""
import re

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app import models, schemas
from app.models import utcnow
from app.services.data import rules_by_id

_QUOTED = re.compile(r'"([^"]+)"')


def issue_key(rule_id: str, message: str) -> str:
    """Clave extra de identidad. Para reglas required_parameters (R05) el plugin emite un issue por parámetro:
    la clave es el parámetro citado en el mensaje (o el mensaje completo si no hay comillas). Resto: ""."""
    rule = rules_by_id().get(rule_id)
    if rule and rule["check"] == "required_parameters":
        m = _QUOTED.search(message or "")
        return m.group(1) if m else (message or "")
    return ""


def _key(guid, rule_id, related, key=""):
    return (guid, rule_id, related, key)


def ingest_snapshot(db: Session, payload: schemas.SnapshotCreate) -> models.Snapshot:
    now = utcnow()
    snap = db.scalars(
        select(models.Snapshot).where(
            models.Snapshot.project_code == payload.project_code,
            models.Snapshot.version_label == payload.version_label,
        )
    ).first()
    if snap is None:
        snap = models.Snapshot(project_code=payload.project_code, version_label=payload.version_label)
        db.add(snap)
    else:  # reenvío: se reemplaza el contenido, se conserva el id
        snap.elements.clear()
        db.execute(delete(models.SnapshotIssue).where(models.SnapshotIssue.snapshot_id == snap.id))
    snap.file_name = payload.file_name
    snap.cde_state = payload.cde_state
    snap.rules_version = payload.rules_version
    snap.author = payload.author
    snap.created_at = now
    for el in payload.elements:
        snap.elements.append(models.Element(**el.model_dump()))
    db.flush()

    discipline_by_guid: dict[str, str] = {}
    for el in payload.elements:
        discipline_by_guid.setdefault(el.guid, el.discipline)

    existing = {
        _key(i.element_guid, i.rule_id, i.related_guid, i.issue_key): i
        for i in db.scalars(select(models.Issue).where(models.Issue.project_code == payload.project_code))
    }
    present: set[tuple] = set()
    for ic in payload.issues:
        ikey = issue_key(ic.rule_id, ic.message)
        k = _key(ic.element_guid, ic.rule_id, ic.related_guid, ikey)
        if k in present:
            continue  # duplicado dentro del mismo envío
        present.add(k)
        issue = existing.get(k)
        if issue is None:
            issue = models.Issue(
                project_code=payload.project_code,
                element_guid=ic.element_guid,
                rule_id=ic.rule_id,
                related_guid=ic.related_guid,
                issue_key=ikey,
                status="open",
                first_seen_at=now,
                first_snapshot_id=snap.id,
            )
            db.add(issue)
            existing[k] = issue
            opened = True
        else:
            opened = issue.status == "fixed"  # reaparece: regresión, se reabre
            if opened:
                issue.status = "open"
                issue.resolved_at = None
                issue.fixed_by = None
        issue.severity = ic.severity
        issue.message = ic.message
        issue.snapshot_id = snap.id
        issue.discipline = discipline_by_guid.get(ic.element_guid) if ic.element_guid else None
        db.flush()
        if opened:
            db.add(models.IssueEvent(issue_id=issue.id, kind="opened", at=now, snapshot_id=snap.id))
        db.add(models.SnapshotIssue(snapshot_id=snap.id, issue_id=issue.id, status=issue.status))

    # Los abiertos que ya no vienen se dan por corregidos.
    for k, issue in existing.items():
        if k not in present and issue.status == "open":
            issue.status = "fixed"
            issue.resolved_at = now
            issue.fixed_by = issue.fixed_by or "manual"
            db.add(models.IssueEvent(issue_id=issue.id, kind="fixed", at=now, snapshot_id=snap.id))

    db.commit()
    db.refresh(snap)
    return snap


def update_issue(db: Session, issue: models.Issue, body: schemas.IssueUpdate) -> models.Issue:
    now = utcnow()
    if body.status != issue.status:
        if body.status == "open":
            issue.resolved_at = None
            issue.fixed_by = None
            kind = "opened"
        else:
            issue.resolved_at = now
            kind = body.status
        issue.status = body.status
        db.add(models.IssueEvent(issue_id=issue.id, kind=kind, at=now, snapshot_id=issue.snapshot_id))
    if body.status == "fixed":
        issue.fixed_by = body.fixed_by or issue.fixed_by or "manual"
    link = db.get(models.SnapshotIssue, (issue.snapshot_id, issue.id))
    if link is not None:
        link.status = issue.status
    db.commit()
    db.refresh(issue)
    return issue
