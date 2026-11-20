import pytest

from conftest import ELEMENTS_V1, el, snapshot_body


def lines_by_code(budget):
    return {l["partida_codigo"]: l for l in budget["lines"]}


def test_budget_hand_computed(client):
    s = client.post("/api/snapshots", json=snapshot_body()).json()
    b = client.get("/api/budget", params={"snapshot_id": s["id"]}).json()
    L = lines_by_code(b)
    # Placas: W1 (2.0 m3, 8 m2; duplicado una vez) + W5 (1.0 m3, área 0)
    assert L["OE.2.3.5.1"]["cantidad"] == 3.0 and L["OE.2.3.5.1"]["subtotal"] == 1500.0
    assert L["OE.2.3.5.1"]["element_count"] == 2
    assert L["OE.2.3.5.2"]["cantidad"] == 16.0 and L["OE.2.3.5.2"]["subtotal"] == 880.0
    assert L["OE.2.3.5.2"]["element_count"] == 1
    # Columnas C1 0.48 + C2 0.5 = 0.98 m3 → tres partidas desde un código
    assert L["OE.2.3.6.1"]["cantidad"] == 0.98 and L["OE.2.3.6.1"]["subtotal"] == 509.6
    assert L["OE.2.3.6.2"]["cantidad"] == 9.8 and L["OE.2.3.6.2"]["subtotal"] == 568.4
    assert L["OE.2.3.6.3"]["cantidad"] == 117.6 and L["OE.2.3.6.3"]["subtotal"] == 611.52
    assert L["OE.2.3.6.3"]["unidad"] == "kg" and L["OE.2.3.6.3"]["uniclass_codes"] == ["Ss_20_10_10"]
    # Puerta: count = 1
    assert L["OE.3.9.1.1"]["cantidad"] == 1.0 and L["OE.3.9.1.1"]["subtotal"] == 650.0
    assert L["OE.3.9.1.1"]["unidad"] == "und" and L["OE.3.9.1.1"]["pendiente_validar"] is True
    assert set(L) == {"OE.2.3.5.1", "OE.2.3.5.2", "OE.2.3.6.1", "OE.2.3.6.2", "OE.2.3.6.3", "OE.3.9.1.1"}
    assert b["total"] == 4719.52
    assert b["currency"] == "PEN" and b["is_official"] is False and b["cde_state"] == "WIP"
    u = b["unbudgeted"]
    assert u["by_reason"] == {"sin_codigo": 2, "codigo_invalido": 2, "sin_mapeo": 0, "sin_cantidad": 2}
    assert u["element_count"] == 6
    assert set(u["guids_sample"]) == {"W2", "B1", "W3", "W4", "F1", "W5"}
    assert b["overlap_warnings"] == 1


def test_budget_sin_mapeo(client, monkeypatch):
    from app.services import budget as budget_mod
    real = budget_mod.mapping_by_code()
    monkeypatch.setattr(budget_mod, "mapping_by_code", lambda: {k: v for k, v in real.items() if k != "Ss_25_30_20"})
    client.post("/api/snapshots", json=snapshot_body())
    b = client.get("/api/budget").json()
    assert b["unbudgeted"]["by_reason"]["sin_mapeo"] == 1
    assert "OE.3.9.1.1" not in lines_by_code(b)


def test_budget_official_only_published(client):
    s = client.post("/api/snapshots", json=snapshot_body(issues=[])).json()
    client.patch(f"/api/snapshots/{s['id']}/cde-state", json={"cde_state": "SHARED"})
    assert client.get("/api/budget").json()["is_official"] is False
    client.patch(f"/api/snapshots/{s['id']}/cde-state", json={"cde_state": "PUBLISHED"})
    assert client.get("/api/budget").json()["is_official"] is True
    assert client.get("/api/budget", params={"snapshot_id": 99}).status_code == 404


def test_budget_diff(client):
    s1 = client.post("/api/snapshots", json=snapshot_body("v1")).json()
    v2 = [e for e in ELEMENTS_V1 if e["guid"] != "D1"]
    v2 = [dict(e, volume_m3=0.6) if e["guid"] == "C2" else e for e in v2]
    v2.append(el("V1", "OST_Windows", "Ss_25_30_95", area_m2=1.8))
    s2 = client.post("/api/snapshots", json=snapshot_body("v2", elements=v2)).json()
    d = client.get("/api/budget/diff", params={"from_snapshot_id": s1["id"], "to_snapshot_id": s2["id"]}).json()
    L = {l["partida_codigo"]: l for l in d["lines"]}
    assert L["OE.3.9.1.1"]["change"] == "removed" and L["OE.3.9.1.1"]["delta_subtotal"] == -650.0
    assert L["OE.3.10.1.1"]["change"] == "added" and L["OE.3.10.1.1"]["subtotal_to"] == 504.0
    assert L["OE.2.3.6.1"]["change"] == "changed"
    assert L["OE.2.3.6.1"]["cantidad_from"] == 0.98 and L["OE.2.3.6.1"]["cantidad_to"] == 1.08
    assert L["OE.2.3.5.1"]["change"] == "unchanged"
    # Δ columnas 0.1 m3: 52 + 58 + 62.4 = 172.4 ; -650 puerta ; +504 ventana
    assert d["total_from"] == 4719.52
    assert d["delta_total"] == pytest.approx(26.4)
    assert d["total_to"] == pytest.approx(4745.92)
    assert d["delta_pct"] == round(26.4 / 4719.52 * 100, 2)
    assert (d["elements_added"], d["elements_removed"], d["elements_modified"]) == (1, 1, 1)
    assert client.get("/api/budget/diff", params={"from_snapshot_id": 1, "to_snapshot_id": 99}).status_code == 404


def test_stats(client):
    s1 = client.post("/api/snapshots", json=snapshot_body("v1")).json()
    client.post("/api/feedback", json={"element_guid": "W2", "rule_id": "R02", "reason": "no_encuentro_codigo"})
    client.post("/api/feedback", json={"element_guid": "B1", "rule_id": "R02", "reason": "no_encuentro_codigo"})
    client.post("/api/feedback", json={"element_guid": "C1", "rule_id": "R05", "reason": "falta_informacion"})
    st = client.get("/api/stats").json()
    assert st["snapshot_id"] == s1["id"] and st["element_count"] == 10
    # bloqueados: W2, W1 (R04), C1, B1 → 6 de 10 conformes
    assert st["conformance_pct"] == 60.0
    assert st["can_move_to_shared"] is False
    D = {d["discipline"]: d for d in st["by_discipline"]}
    assert D["ARQ"]["element_count"] == 7 and D["ARQ"]["conforming_count"] == 5
    assert D["ARQ"]["open_errors"] == 1 and D["ARQ"]["open_warnings"] == 1
    assert D["EST"]["element_count"] == 3 and D["EST"]["conforming_count"] == 1
    assert D["EST"]["open_errors"] == 1 and D["EST"]["open_warnings"] == 1
    R = {r["rule_id"]: r for r in st["by_rule"]}
    assert R["R02"]["open_count"] == 2 and R["R02"]["feedback_count"] == 2
    assert R["R02"]["rule_name"] == "Elemento sin código Uniclass"
    assert R["R01"]["open_count"] == 0 and len(R) == 7
    assert st["feedback_by_reason"] == {"no_encuentro_codigo": 2, "falta_informacion": 1}
    assert st["snapshots_by_cde_state"] == {"WIP": 1}

    c1 = next(i for i in client.get("/api/issues").json() if i["rule_id"] == "R05")
    client.patch(f"/api/issues/{c1['id']}", json={"status": "fixed", "fixed_by": "one_click"})
    client.post("/api/snapshots", json=snapshot_body("v2", issues=[]))
    st2 = client.get("/api/stats").json()
    assert st2["conformance_pct"] == 100.0 and st2["can_move_to_shared"] is True
    assert st2["fixed_one_click"] == 1 and st2["fixed_manual"] == 4
    assert {r["rule_id"]: r["fixed_count"] for r in st2["by_rule"]}["R02"] == 2
    assert st2["snapshots_by_cde_state"] == {"WIP": 2}
    # el snapshot viejo conserva su foto
    assert client.get("/api/stats", params={"snapshot_id": s1["id"]}).json()["conformance_pct"] == 70.0  # R05 se corrigió por PATCH en v1


def test_stats_empty_404(client):
    assert client.get("/api/stats").status_code == 404
    assert client.get("/api/ai/recommendations").status_code == 404
