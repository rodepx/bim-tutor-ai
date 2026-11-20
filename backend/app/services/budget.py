"""Motor de presupuesto 5D (BEP §8)."""
from sqlalchemy.orm import Session

from app import models
from app.services.common import snapshot_issues, unique_elements
from app.services.data import mapping_by_code, uniclass_by_code

REASONS = ("sin_codigo", "codigo_invalido", "sin_mapeo", "sin_cantidad")
MAGNITUDES = ("volume_m3", "area_m2", "length_m")


def magnitude(el, fuente: str) -> float | None:
    if fuente == "count":
        return 1.0
    return getattr(el, fuente, None) if fuente in MAGNITUDES else None


def compute_lines(elements) -> tuple[dict[str, dict], dict[str, str]]:
    """Devuelve (líneas por partida, motivo de no presupuestado por guid). `elements` ya deduplicados."""
    uniclass = uniclass_by_code()
    mapping = mapping_by_code()
    lines: dict[str, dict] = {}
    unbudgeted: dict[str, str] = {}
    for el in elements:
        code = (el.classification_code or "").strip()
        if not code:
            unbudgeted[el.guid] = "sin_codigo"
            continue
        uc = uniclass.get(code)
        if uc is None or el.category not in uc["revit_categories"]:
            unbudgeted[el.guid] = "codigo_invalido"
            continue
        rows = mapping.get(code)
        if not rows:
            unbudgeted[el.guid] = "sin_mapeo"
            continue
        for row in rows:
            mag = magnitude(el, row["magnitud_fuente"])
            if not mag:  # None o 0
                unbudgeted.setdefault(el.guid, "sin_cantidad")
                continue
            line = lines.setdefault(row["partida_codigo"], {
                "partida_codigo": row["partida_codigo"],
                "descripcion": row["descripcion"],
                "unidad": row["unidad"],
                "cantidad": 0.0,
                "precio_unitario": row["precio_unitario"],
                "guids": set(),
                "uniclass_codes": set(),
                "pendiente_validar": False,
            })
            line["cantidad"] += mag * row["factor"]
            line["guids"].add(el.guid)
            line["uniclass_codes"].add(code)
            if "PENDIENTE" in row["estado"].upper():
                line["pendiente_validar"] = True
    return lines, unbudgeted


def compute_budget(db: Session, snap: models.Snapshot) -> dict:
    elements = unique_elements(snap)
    raw, unbudgeted = compute_lines(elements)
    lines = []
    for code in sorted(raw):
        r = raw[code]
        cantidad = round(r["cantidad"], 3)
        lines.append({
            "partida_codigo": code,
            "descripcion": r["descripcion"],
            "unidad": r["unidad"],
            "cantidad": cantidad,
            "precio_unitario": r["precio_unitario"],
            "subtotal": round(cantidad * r["precio_unitario"], 2),
            "element_count": len(r["guids"]),
            "uniclass_codes": sorted(r["uniclass_codes"]),
            "pendiente_validar": r["pendiente_validar"],
        })
    by_reason = {k: 0 for k in REASONS}
    for reason in unbudgeted.values():
        by_reason[reason] += 1
    overlap = sum(1 for i in snapshot_issues(db, snap.id) if i.rule_id == "R04")
    return {
        "snapshot_id": snap.id,
        "cde_state": snap.cde_state,
        "is_official": snap.cde_state == "PUBLISHED",
        "currency": "PEN",
        "total": round(sum(l["subtotal"] for l in lines), 2),
        "lines": lines,
        "unbudgeted": {
            "element_count": len(unbudgeted),
            "guids_sample": list(unbudgeted)[:20],
            "by_reason": by_reason,
        },
        "overlap_warnings": overlap,
    }


def _signature(el) -> tuple:
    return (el.type_name, el.classification_code, el.volume_m3, el.area_m2, el.length_m)


def compute_diff(db: Session, a: models.Snapshot, b: models.Snapshot) -> dict:
    ba, bb = compute_budget(db, a), compute_budget(db, b)
    la = {l["partida_codigo"]: l for l in ba["lines"]}
    lb = {l["partida_codigo"]: l for l in bb["lines"]}
    lines = []
    for code in sorted(set(la) | set(lb)):
        f, t = la.get(code), lb.get(code)
        ref = t or f
        cf, ct = (f["cantidad"] if f else 0.0), (t["cantidad"] if t else 0.0)
        sf, st = (f["subtotal"] if f else 0.0), (t["subtotal"] if t else 0.0)
        if f is None:
            change = "added"
        elif t is None:
            change = "removed"
        elif cf != ct or sf != st:
            change = "changed"
        else:
            change = "unchanged"
        lines.append({
            "partida_codigo": code,
            "descripcion": ref["descripcion"],
            "unidad": ref["unidad"],
            "cantidad_from": cf,
            "cantidad_to": ct,
            "subtotal_from": sf,
            "subtotal_to": st,
            "delta_subtotal": round(st - sf, 2),
            "change": change,
        })
    ea = {e.guid: e for e in unique_elements(a)}
    eb = {e.guid: e for e in unique_elements(b)}
    delta = round(bb["total"] - ba["total"], 2)
    return {
        "from_snapshot_id": a.id,
        "to_snapshot_id": b.id,
        "total_from": ba["total"],
        "total_to": bb["total"],
        "delta_total": delta,
        "delta_pct": round(delta / ba["total"] * 100, 2) if ba["total"] else None,
        "lines": lines,
        "elements_added": len(eb.keys() - ea.keys()),
        "elements_removed": len(ea.keys() - eb.keys()),
        "elements_modified": sum(1 for g in ea.keys() & eb.keys() if _signature(ea[g]) != _signature(eb[g])),
    }
