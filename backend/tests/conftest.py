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
