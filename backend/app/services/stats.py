"""Salud del modelo (GET /stats) y `facts` para recomendaciones de la IA."""
from collections import Counter

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models
from app.services.budget import compute_budget, compute_diff
from app.services.common import previous_snapshot, snapshot_issues, unique_elements
from app.services.data import load_rules, rule_name, rules_by_id


def _pct(num: int, den: int) -> float:
    return round(num / den * 100, 1) if den else 0.0


def compute_stats(db: Session, snap: models.Snapshot) -> dict:
    elements = unique_elements(snap)
    open_issues = snapshot_issues(db, snap.id, "open")
    blocking = {i.element_guid for i in open_issues if i.severity in ("error", "warning") and i.element_guid}
    conforming = [e for e in elements if e.guid not in blocking]

    disciplines = list(load_rules()["disciplines"].keys())
    for e in elements:
        if e.discipline not in disciplines:
            disciplines.append(e.discipline)
    by_discipline = []
    for d in disciplines:
        els = [e for e in elements if e.discipline == d]
        conf = [e for e in els if e.guid not in blocking]
        by_discipline.append({
            "discipline": d,
            "element_count": len(els),
            "conforming_count": len(conf),
            "conformance_pct": _pct(len(conf), len(els)),
            "open_errors": sum(1 for i in open_issues if i.discipline == d and i.severity == "error"),
            "open_warnings": sum(1 for i in open_issues if i.discipline == d and i.severity == "warning"),
        })

    project_issues = list(db.scalars(select(models.Issue).where(models.Issue.project_code == snap.project_code)))
    fixed = [i for i in project_issues if i.status == "fixed"]
    open_by_rule = Counter(i.rule_id for i in open_issues)
    fixed_by_rule = Counter(i.rule_id for i in fixed)
    fb_by_rule = dict(db.execute(select(models.Feedback.rule_id, func.count()).group_by(models.Feedback.rule_id)).all())
    rule_ids = list(rules_by_id().keys())
    for rid in list(open_by_rule) + list(fixed_by_rule):
        if rid not in rule_ids:
            rule_ids.append(rid)
    by_rule = [
        {
            "rule_id": rid,
            "rule_name": rule_name(rid),
            "open_count": open_by_rule.get(rid, 0),
            "fixed_count": fixed_by_rule.get(rid, 0),
            "feedback_count": fb_by_rule.get(rid, 0),
        }
        for rid in rule_ids
    ]

    feedback_by_reason = dict(
        db.execute(select(models.Feedback.reason, func.count()).group_by(models.Feedback.reason)).all()
    )
    snapshots_by_cde_state = dict(
        db.execute(
            select(models.Snapshot.cde_state, func.count())
            .where(models.Snapshot.project_code == snap.project_code)
            .group_by(models.Snapshot.cde_state)
        ).all()
    )
    open_errors = sum(1 for i in open_issues if i.severity == "error")
    return {
        "snapshot_id": snap.id,
        "cde_state": snap.cde_state,
        "element_count": len(elements),
        "conformance_pct": _pct(len(conforming), len(elements)),
        "can_move_to_shared": open_errors == 0,
        "by_discipline": by_discipline,
        "by_rule": by_rule,
        "feedback_by_reason": feedback_by_reason,
        "snapshots_by_cde_state": snapshots_by_cde_state,
        "fixed_one_click": sum(1 for i in fixed if i.fixed_by == "one_click"),
        "fixed_manual": sum(1 for i in fixed if i.fixed_by == "manual"),
    }


def compute_facts(db: Session, snap: models.Snapshot) -> dict:
    """Hechos calculados por SQL/servicios para build_recommendations (ver backend/README.md)."""
    stats = compute_stats(db, snap)
    budget = compute_budget(db, snap)
    open_issues = snapshot_issues(db, snap.id, "open")

    top = max((r for r in stats["by_rule"] if r["open_count"] > 0), key=lambda r: r["open_count"], default=None)
    fb = stats["feedback_by_reason"]
    fb_top = max(fb.items(), key=lambda kv: kv[1], default=None)
    prev = previous_snapshot(db, snap)
    diff = compute_diff(db, prev, snap) if prev else None

    return {
        "snapshot_id": snap.id,
        "project_code": snap.project_code,
        "version_label": snap.version_label,
        "cde_state": snap.cde_state,
        "is_official": budget["is_official"],
        "element_count": stats["element_count"],
        "conformance_pct": stats["conformance_pct"],
        "open_errors": sum(1 for i in open_issues if i.severity == "error"),
        "open_warnings": sum(1 for i in open_issues if i.severity == "warning"),
        "can_move_to_shared": stats["can_move_to_shared"],
        "top_rule_id": top["rule_id"] if top else None,
        "top_rule_name": top["rule_name"] if top else None,
        "top_rule_open_count": top["open_count"] if top else 0,
        "budget_total": budget["total"],
        "unbudgeted_count": budget["unbudgeted"]["element_count"],
        "unbudgeted_sin_codigo": budget["unbudgeted"]["by_reason"]["sin_codigo"],
        "unbudgeted_codigo_invalido": budget["unbudgeted"]["by_reason"]["codigo_invalido"],
        "unbudgeted_sin_mapeo": budget["unbudgeted"]["by_reason"]["sin_mapeo"],
        "unbudgeted_sin_cantidad": budget["unbudgeted"]["by_reason"]["sin_cantidad"],
        "overlap_warnings": budget["overlap_warnings"],
        "previous_snapshot_id": prev.id if prev else None,
        "previous_version_label": prev.version_label if prev else None,
        "delta_total": diff["delta_total"] if diff else None,
        "delta_pct": diff["delta_pct"] if diff else None,
        "feedback_top_reason": fb_top[0] if fb_top else None,
        "feedback_top_count": fb_top[1] if fb_top else 0,
        "fixed_one_click": stats["fixed_one_click"],
        "fixed_manual": stats["fixed_manual"],
    }
