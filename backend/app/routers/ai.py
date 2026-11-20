"""Rutas /ai/*. El backend arma rule/candidates/facts; el módulo app.ai solo redacta."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import schemas
from app.ai import build_recommendations, explain_rule, suggest_classification
from app.db import get_db
from app.services.common import resolve_snapshot
from app.services.data import rules_by_id, uniclass_public
from app.services.stats import compute_facts

router = APIRouter(prefix="/ai", tags=["ia"])


@router.post("/explain", response_model=schemas.Explanation, responses={404: {"model": schemas.Error}})
def explain(body: schemas.ExplainRequest):
    rule = rules_by_id().get(body.rule_id)
    if rule is None:
        raise HTTPException(404, f"Regla {body.rule_id} no existe")
    element = body.element.model_dump() if body.element else None
    return explain_rule(rule, element)


@router.post("/suggest-classification", response_model=schemas.ClassificationSuggestion)
def suggest(body: schemas.SuggestRequest):
    element = body.element.model_dump()
    candidates = uniclass_public(body.element.category)
    result = dict(suggest_classification(element, candidates))
    # Garantía del contrato: suggested_code siempre es uno de candidates o null.
    if result.get("suggested_code") not in {c["code"] for c in candidates}:
        result["suggested_code"] = None
    result["candidates"] = candidates
    result.setdefault("element_guid", body.element.guid)
    return result


@router.get("/recommendations", response_model=list[schemas.Recommendation], responses={404: {"model": schemas.Error}})
def recommendations(snapshot_id: int | None = None, db: Session = Depends(get_db)):
    facts = compute_facts(db, resolve_snapshot(db, snapshot_id))
    recs = build_recommendations(facts)
    out = []
    for r in recs:
        r = dict(r)
        # facts del contrato: number | string. Se omiten null; bool → 0/1.
        r["facts"] = {
            k: (int(v) if isinstance(v, bool) else v) for k, v in (r.get("facts") or {}).items() if v is not None
        }
        out.append(r)
    return out
