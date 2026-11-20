import copy
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from fastapi.testclient import TestClient  # noqa: E402

from app import db  # noqa: E402
from app.main import app  # noqa: E402
from app.routers import ai as ai_router  # noqa: E402
from app.routers import system as system_router  # noqa: E402


@pytest.fixture
def client(tmp_path, monkeypatch):
    db.configure(f"sqlite:///{(tmp_path / 'test.db').as_posix()}")
    # IA determinista para los tests del backend (el módulo app.ai tiene sus propios tests).
    monkeypatch.setattr(system_router, "llm_mode", lambda: "mock")
    monkeypatch.setattr(ai_router, "explain_rule", lambda rule, element: {
        "rule_id": rule["id"], "text": rule["explanation"], "cached": False, "mode": "mock"})
    monkeypatch.setattr(ai_router, "suggest_classification", lambda element, candidates: {
        "element_guid": element["guid"], "candidates": candidates,
        "suggested_code": candidates[0]["code"] if candidates else None, "reason": "test", "mode": "mock"})
    monkeypatch.setattr(ai_router, "build_recommendations", lambda facts: [{
        "id": "rec1", "title": "t", "text": f"{facts['open_errors']}", "priority": "alta",
        "facts": {"open_errors": facts["open_errors"], "delta_pct": facts["delta_pct"],
                  "can_move_to_shared": facts["can_move_to_shared"]}, "mode": "mock"}])
    with TestClient(app) as c:
        yield c
    db.engine.dispose()


def el(guid, category, code=None, discipline=None, type_name="TIPO_OK", level="Nivel 1", **mags):
    disc = discipline or ("EST" if category.startswith("OST_Structural") else "ARQ")
    return {"guid": guid, "category": category, "discipline": disc, "type_name": type_name,
            "classification_code": code, "level": level,
            "volume_m3": mags.get("volume_m3"), "area_m2": mags.get("area_m2"), "length_m": mags.get("length_m")}


# Ejemplo calculado a mano (ver test_budget.py)
ELEMENTS_V1 = [
    el("W1", "OST_Walls", "Ss_25_10_20", volume_m3=2.0, area_m2=8.0),
    el("W1", "OST_Walls", "Ss_25_10_20", volume_m3=2.0, area_m2=8.0),  # guid duplicado: cuenta una vez
    el("C1", "OST_StructuralColumns", "Ss_20_10_10", volume_m3=0.48),
    el("C2", "OST_StructuralColumns", "Ss_20_10_10", volume_m3=0.5),
    el("D1", "OST_Doors", "Ss_25_30_20", area_m2=1.89),
    el("W2", "OST_Walls", None, area_m2=10.0),                       # sin_codigo
    el("W3", "OST_Walls", "Ss_20_10_10", volume_m3=1.0),             # código de columna en muro → codigo_invalido
    el("W4", "OST_Walls", "Ss_99_99_99", volume_m3=1.0),             # inexistente → codigo_invalido
    el("F1", "OST_Floors", "Ss_30_10_35", area_m2=None),             # sin_cantidad
    el("W5", "OST_Walls", "Ss_25_10_20", volume_m3=1.0, area_m2=0),  # encofrado sin área → sin_cantidad (una vez)
    el("B1", "OST_StructuralFraming", None, volume_m3=0.3),          # sin_codigo
]

ISSUES_V1 = [
    {"element_guid": "W2", "rule_id": "R02", "severity": "error", "message": "sin código"},
    {"element_guid": "W1", "rule_id": "R04", "severity": "warning", "message": "overlap", "related_guid": "B1"},
    {"element_guid": None, "rule_id": "R06", "severity": "warning", "message": "nombre archivo"},
    {"element_guid": "C1", "rule_id": "R05", "severity": "warning", "message": "falta fc"},
    {"element_guid": "B1", "rule_id": "R02", "severity": "error", "message": "sin código"},
]


def snapshot_body(version="v1", elements=None, issues=None, cde_state="WIP", project="HKT"):
    return {
        "project_code": project, "file_name": "HKT-EQP-ZZ-ZZ-M3-S-0001", "version_label": version,
        "cde_state": cde_state, "rules_version": "0.1.0", "author": "tester",
        "elements": copy.deepcopy(ELEMENTS_V1 if elements is None else elements),
        "issues": copy.deepcopy(ISSUES_V1 if issues is None else issues),
    }
