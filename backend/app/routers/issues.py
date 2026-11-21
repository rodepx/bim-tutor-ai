from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models, schemas
from app.db import get_db
from app.services.common import element_dict, resolve_snapshot
from app.services.snapshots import update_issue as do_update_issue

router = APIRouter(tags=["issues"])

_KIND = {"opened": "issue_opened", "fixed": "issue_fixed", "dismissed": "issue_dismissed"}


@router.get("/issues", response_model=list[schemas.Issue])
def list_issues(
    snapshot_id: int | None = None,
    status: schemas.IssueStatus | None = None,
    discipline: schemas.Discipline | None = None,
    rule_id: str | None = None,
    element_guid: str | None = None,
    db: Session = Depends(get_db),
):
    snap = resolve_snapshot(db, snapshot_id)
    rows = db.execute(
        select(models.Issue, models.SnapshotIssue.status)
        .join(models.SnapshotIssue, models.SnapshotIssue.issue_id == models.Issue.id)
        .where(models.SnapshotIssue.snapshot_id == snap.id)
        .order_by(models.Issue.id)
    ).all()
    # El estado que se filtra y devuelve es el del issue dentro de este snapshot (contrato 0.2.0).
    return [
        schemas.Issue.model_validate(i).model_copy(update={"status": st})
        for i, st in rows
        if (status is None or st == status)
        and (discipline is None or i.discipline == discipline)
        and (rule_id is None or i.rule_id == rule_id)
        and (element_guid is None or i.element_guid == element_guid)
    ]


@router.patch("/issues/{issue_id}", response_model=schemas.Issue, responses={404: {"model": schemas.Error}})
def update_issue(issue_id: int, body: schemas.IssueUpdate, db: Session = Depends(get_db)):
    issue = db.get(models.Issue, issue_id)
    if issue is None:
        raise HTTPException(404, f"Issue {issue_id} no existe")
    return do_update_issue(db, issue, body)


@router.get("/elements/{guid}/thread", response_model=schemas.ElementThread, responses={404: {"model": schemas.Error}})
def element_thread(guid: str, db: Session = Depends(get_db)):
    latest = db.scalars(
        select(models.Element)
        .join(models.Snapshot)
        .where(models.Element.guid == guid)
        .order_by(models.Snapshot.created_at.desc(), models.Snapshot.id.desc())
        .limit(1)
    ).first()
    issues = {i.id: i for i in db.scalars(select(models.Issue).where(models.Issue.element_guid == guid))}
    feedback = list(db.scalars(select(models.Feedback).where(models.Feedback.element_guid == guid)))
    if latest is None and not issues and not feedback:
        raise HTTPException(404, f"Elemento {guid} no existe")

    events = []
    if issues:
        for ev in db.scalars(select(models.IssueEvent).where(models.IssueEvent.issue_id.in_(issues.keys()))):
            events.append((ev.at, ev.id, {"at": ev.at, "kind": _KIND[ev.kind], "snapshot_id": ev.snapshot_id,
                                         "issue": issues[ev.issue_id]}))
    for fb in feedback:
        issue = issues.get(fb.issue_id) if fb.issue_id else None
        events.append((fb.created_at, 0, {"at": fb.created_at, "kind": "feedback",
                                          "snapshot_id": issue.snapshot_id if issue else None, "feedback": fb}))
    events.sort(key=lambda t: (t[0], t[1]))
    return {"guid": guid, "latest": element_dict(latest) if latest else None, "events": [e[2] for e in events]}
