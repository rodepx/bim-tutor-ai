import csv
import json

import httpx
import pytest

from app import ai
from app.ai.guard import check_text
from conftest import REPO

RULES = json.loads((REPO / "data" / "rules.json").read_text(encoding="utf-8"))["rules"]
R02 = next(r for r in RULES if r["id"] == "R02")


def _uniclass():
    with open(REPO / "data" / "uniclass_subset.csv", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        r["revit_categories"] = r["revit_categories"].split(";")
    return rows


def _cands(cat):
    return [c for c in _uniclass() if cat in c["revit_categories"]]


WALL = {"guid": "g-1", "category": "OST_Walls", "type_name": "MUR_CA_e25_FC210", "family_name": "Muro básico",
        "level": "Nivel 1", "parameters": {}}

FACTS = {
    "conformance_pct": 72.5, "open_errors": 14, "open_warnings": 6, "top_rule_id": "R02",
    "top_rule_name": "Elemento sin código Uniclass", "top_rule_open_count": 9, "budget_total": 1234567.8,
    "unbudgeted_count": 9, "unbudgeted_sin_codigo": 7, "overlap_warnings": 3, "delta_total": 12345.5,
    "delta_pct": 4.25, "feedback_top_reason": "falso positivo", "feedback_top_count": 4,
    "cde_state": "WIP", "can_move_to_shared": False,
}


# ------------------------------------------------------------------ modo
def test_mock_mode_without_key(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    assert ai.llm_mode() == "mock"
    res = ai.explain_rule(R02, None)
    assert res["mode"] == "mock"
    assert res["text"].startswith(R02["explanation"])
    assert "Cómo corregirlo: Asignar código sugerido" in res["text"]
    recs = ai.build_recommendations(FACTS)
    assert all(r["mode"] == "mock" for r in recs)


def test_provider_mock_forces_mock(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    assert ai.llm_mode() == "mock"


def test_network_error_falls_back_to_mock(monkeypatch):
    def boom(*a, **k):
        raise httpx.ConnectError("sin red")

    monkeypatch.setattr("app.ai.llm.httpx.post", boom)
    assert ai.llm_mode() == "openrouter"
    exp = ai.explain_rule(R02, WALL)
    assert exp["mode"] == "mock" and "Cómo corregirlo" in exp["text"]
    sug = ai.suggest_classification(WALL, _cands("OST_Walls"))
    assert sug["mode"] == "mock" and sug["suggested_code"] == "Ss_25_10_20"
    recs = ai.build_recommendations(FACTS)
    assert recs and all(r["mode"] == "mock" for r in recs)


def test_http_error_falls_back_to_mock(fake_llm):
    from conftest import FakeResp

    fake_llm.answers = lambda kw: FakeResp("", status=500)
    assert ai.explain_rule(R02, None)["mode"] == "mock"


# ------------------------------------------------------------------ explain_rule
def test_explain_cache_hit_no_second_http(fake_llm):
    fake_llm.answers = ["Texto didáctico del LLM sobre la §4 del BEP."]
    first = ai.explain_rule(R02, WALL)
    assert first["cached"] is False and first["mode"] == "openrouter"
    assert first["text"].startswith("Texto didáctico del LLM")
    assert "MUR_CA_e25_FC210" in first["text"]  # ejemplo personalizado fuera de la caché
    second = ai.explain_rule(R02, None)
    assert second["cached"] is True
    assert second["text"] == "Texto didáctico del LLM sobre la §4 del BEP."
    assert len(fake_llm.calls) == 1


def test_explain_cache_persists_on_disk(fake_llm):
    from app.ai import service

    fake_llm.answers = ["Explicación persistida."]
    ai.explain_rule(R02, None)
    service.clear_memory_cache()
    again = ai.explain_rule(R02, None)
    assert again["cached"] is True and again["text"] == "Explicación persistida."
    assert len(fake_llm.calls) == 1


def test_explain_cache_invalidates_on_rule_change(fake_llm):
    fake_llm.answers = ["v1", "v2"]
    ai.explain_rule(R02, None)
    changed = {**R02, "explanation": R02["explanation"] + " Nuevo."}
    res = ai.explain_rule(changed, None)
    assert res["cached"] is False and res["text"] == "v2"


# ------------------------------------------------------------------ suggest_classification
def test_mock_suggestion_concrete_wall(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    res = ai.suggest_classification(WALL, _cands("OST_Walls"))
    assert res["suggested_code"] == "Ss_25_10_20"
    assert res["mode"] == "mock" and res["element_guid"] == "g-1"


@pytest.mark.parametrize("type_name,cat,expected", [
    ("MUR_LAD_e15", "OST_Walls", "Ss_25_10_50"),
    ("MUR_DRYWALL_e10", "OST_Walls", "Ss_25_10_30"),
    ("LOS_ALIG_e20", "OST_Floors", "Ss_30_10_35"),
    ("LOS_MAC_e20_FC210", "OST_Floors", "Ss_30_10_30"),
    ("PTA_MAD_090x210", "OST_Doors", "Ss_25_30_20"),
    ("Genérico 200mm", "OST_Walls", None),
])
def test_mock_suggestion_keywords(monkeypatch, type_name, cat, expected):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    el = {"guid": "x", "category": cat, "type_name": type_name}
    assert ai.suggest_classification(el, _cands(cat))["suggested_code"] == expected


def test_llm_suggestion_valid(fake_llm):
    fake_llm.answers = ['```json\n{"code": "Ss_25_10_20", "reason": "Muro de concreto armado."}\n```']
    res = ai.suggest_classification(WALL, _cands("OST_Walls"))
    assert res["suggested_code"] == "Ss_25_10_20" and res["mode"] == "openrouter"


def test_llm_suggestion_outside_candidates_is_none(fake_llm):
    fake_llm.answers = ['{"code": "Ss_30_10_30", "reason": "inventado"}']
    res = ai.suggest_classification(WALL, _cands("OST_Walls"))
    assert res["suggested_code"] is None


def test_llm_suggestion_malformed_json_is_none(fake_llm):
    fake_llm.answers = ["Creo que es Ss_25_10_20 {code: sin comillas"]
    res = ai.suggest_classification(WALL, _cands("OST_Walls"))
    assert res["suggested_code"] is None


# ------------------------------------------------------------------ guard
def test_guard_rejects_invented_number():
    facts = {"open_errors": 14, "budget_total": 12345.5}
    ok, bad = check_text("Hay 14 errores y se perderán 37 días.", facts)
    assert not ok and bad == ["37"]


@pytest.mark.parametrize("text", [
    "Hay 14 errores; el presupuesto es S/ 12,345.50 y la conformidad 72.5%.",
    "Presupuesto S/ 12 345,5 con conformidad de 72,5 % y 14 errores.",
    "Conformidad 73% y presupuesto S/12,346 (14 errores, regla R02, modelo 5D).",
    "Total S/ 1,234,567.80 según el metrado.",
])
def test_guard_accepts_fact_numbers_formatted(text):
    facts = {"open_errors": 14, "budget_total": 12345.5, "conformance_pct": 72.5, "big": 1234567.8}
    ok, bad = check_text(text, facts)
    assert ok, bad


def test_recommendations_reject_llm_text_with_invented_number(fake_llm):
    fake_llm.answers = lambda kw: "Hay 999 problemas urgentes que resolver."
    recs = ai.build_recommendations(FACTS)
    assert recs and all(r["mode"] == "mock" for r in recs)
    assert all("999" not in r["text"] for r in recs)


def test_recommendations_accept_llm_text_with_fact_numbers(fake_llm):
    def answer(kw):
        user = kw["json"]["messages"][1]["content"]
        facts = json.loads(user.split("FACTS: ", 1)[1].split("\n", 1)[0])
        nums = [v for v in facts.values() if isinstance(v, (int, float))]
        return "Revisar: " + ", ".join(f"{v:,}" for v in nums) + "." if nums else "Revisar el modelo."

    fake_llm.answers = answer
    recs = ai.build_recommendations(FACTS)
    assert all(r["mode"] == "openrouter" for r in recs)
    assert all(r["text"].startswith("Revisar") for r in recs)


def test_recommendations_shape_and_templates_pass_guard(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    for facts in (FACTS, {}, {k: None for k in FACTS},
                  {"conformance_pct": 100, "open_errors": 0, "cde_state": "WIP", "can_move_to_shared": True,
                   "delta_total": -500.0, "delta_pct": -1.2, "budget_total": 98000}):
        recs = ai.build_recommendations(facts)
        assert 3 <= len(recs) <= 5
        for r in recs:
            assert set(r) >= {"id", "title", "text", "priority", "facts", "mode"}
            assert r["priority"] in ("alta", "media", "baja")
            assert all(isinstance(v, (int, float, str)) and not isinstance(v, bool) for v in r["facts"].values())
            ok, bad = check_text(r["text"], r["facts"])
            assert ok, (r, bad)


# ------------------------------------------------------------------ guard (revisión: casos adversarios)
@pytest.mark.parametrize("text,bad", [
    ("Hay diez errores abiertos.", ["diez"]),
    ("Faltan quince días y doscientos elementos.", ["quince", "doscientos"]),
    ("Se perderán 58elementos del metrado.", ["58"]),
    ("Valor 12xyz inventado.", ["12"]),
    ("Entre 10-20 errores.", ["10", "20"]),
    ("Entrega el 2026-11-19.", ["2026", "11", "19"]),
    ("Costará S/ 1.2 mil.", ["1.2", "mil"]),
    ("Concreto f'c=280 kg/cm2.", ["280"]),
])
def test_guard_rejects_adversarial_numbers(text, bad):
    ok, found = check_text(text, {"open_errors": 14, "budget_total": 1200})
    assert not ok and found == bad


@pytest.mark.parametrize("text", [
    "Regla R04, tipo MUR_CA_e25_FC210, código Ss_20_10_10, presupuesto 5D y 4D.",
    "Hay catorce errores (14) y la conformidad es 72.5 por ciento.",
    "Hay -14 errores en 120m2 de muro.",
])
def test_guard_still_skips_identifiers_and_accepts_facts(text):
    ok, bad = check_text(text, {"open_errors": 14, "conformance_pct": 72.5, "area": 120})
    assert ok, bad


def test_explain_rejects_llm_text_with_invented_number(fake_llm):
    r05 = next(r for r in RULES if r["id"] == "R05")
    fake_llm.answers = ["Usa un concreto f'c=350 para las columnas (BEP §5)."]
    res = ai.explain_rule(r05, None)
    assert res["mode"] == "mock" and "350" not in res["text"]
    assert res["text"].startswith(r05["explanation"])


def test_explain_accepts_numbers_from_rule(fake_llm):
    r05 = next(r for r in RULES if r["id"] == "R05")
    fake_llm.answers = ["Según el BEP §5, f'c=280 y f'c=210 tienen precios distintos (ISO 19650)."]
    res = ai.explain_rule(r05, None)
    assert res["mode"] == "openrouter" and "280" in res["text"]


def test_recommendation_texts_singular(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    facts = {"open_errors": 1, "top_rule_id": "R02", "top_rule_open_count": 1, "unbudgeted_count": 1,
             "overlap_warnings": 1, "feedback_top_reason": "otro", "feedback_top_count": 1,
             "cde_state": "WIP", "can_move_to_shared": False}
    text = " ".join(r["text"] for r in ai.build_recommendations(facts))
    assert "Se detectó 1 superposición muro–viga (R04) que duplica volumen" in text
    assert "Hay 1 error abierto" in text and "1 elemento quedó" in text
    for wrong in ("1 superposiciones", "1 errores", "1 elementos", "1 veces", "1 abiertas"):
        assert wrong not in text
