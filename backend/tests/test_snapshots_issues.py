from bim_test_helpers import ELEMENTS_V1, el, snapshot_body


def test_health_rules_uniclass(client):
    h = client.get("/api/health").json()
    assert h == {"status": "ok", "version": "0.1.0", "llm_mode": "mock"}
    assert client.get("/api/rules").json()["version"] == "0.1.0"
    walls = client.get("/api/uniclass", params={"category": "OST_Walls"}).json()
    codes = {c["code"] for c in walls}
    assert "Ss_25_10_50" in codes and "Ss_20_05_65" in codes and "Ss_20_10_10" not in codes
    assert len(client.get("/api/uniclass").json()) == 12


def test_snapshot_idempotent(client):
    r1 = client.post("/api/snapshots", json=snapshot_body())
    assert r1.status_code == 201
    s1 = r1.json()
    assert s1["element_count"] == 10  # W1 duplicado cuenta una vez
    assert s1["open_issue_count"] == 5
    r2 = client.post("/api/snapshots", json=snapshot_body())
    assert r2.status_code == 201
    s2 = r2.json()
    assert s2["id"] == s1["id"]
    assert s2["open_issue_count"] == 5
    assert len(client.get("/api/snapshots").json()) == 1
    assert len(client.get("/api/issues").json()) == 5
    detail = client.get(f"/api/snapshots/{s1['id']}").json()
    assert len(detail["elements"]) == len(ELEMENTS_V1)
    assert client.get("/api/snapshots/999").status_code == 404


def test_validation_error_shape(client):
    body = snapshot_body()
    body["cde_state"] = "NOPE"
    r = client.post("/api/snapshots", json=body)
    assert r.status_code == 422
    assert isinstance(r.json()["detail"], str)


def test_issue_lifecycle(client):
    s1 = client.post("/api/snapshots", json=snapshot_body("v1")).json()
    issues = {(i["element_guid"], i["rule_id"]): i for i in client.get("/api/issues").json()}
    r02 = issues[("W2", "R02")]
    assert r02["status"] == "open" and r02["discipline"] == "ARQ" and r02["snapshot_id"] == s1["id"]
    assert issues[(None, "R06")]["discipline"] is None
    assert issues[("C1", "R05")]["discipline"] == "EST"

    # El plugin corrige R05 en 1 clic
    r = client.patch(f"/api/issues/{issues[('C1', 'R05')]['id']}", json={"status": "fixed", "fixed_by": "one_click"})
    assert r.status_code == 200 and r.json()["fixed_by"] == "one_click" and r.json()["resolved_at"]
    assert client.patch("/api/issues/9999", json={"status": "fixed"}).status_code == 404

    # v2: R04 y R05 ya no vienen; aparece R01 en V1
    v2_issues = [
        {"element_guid": "W2", "rule_id": "R02", "severity": "error", "message": "sin código"},
        {"element_guid": None, "rule_id": "R06", "severity": "warning", "message": "nombre archivo"},
        {"element_guid": "B1", "rule_id": "R02", "severity": "error", "message": "sin código"},
        {"element_guid": "V1", "rule_id": "R01", "severity": "error", "message": "genérico"},
    ]
    s2 = client.post("/api/snapshots", json=snapshot_body(
        "v2", elements=ELEMENTS_V1 + [el("V1", "OST_Windows", "Ss_25_30_95", area_m2=1.8)], issues=v2_issues)).json()
    assert s2["id"] != s1["id"] and s2["open_issue_count"] == 4

    all_v2 = {(i["element_guid"], i["rule_id"]): i for i in client.get("/api/issues", params={"snapshot_id": s2["id"]}).json()}
    assert all_v2[("W2", "R02")]["id"] == r02["id"]
    assert all_v2[("W2", "R02")]["snapshot_id"] == s2["id"]
    assert all_v2[("W2", "R02")]["first_seen_at"] == r02["first_seen_at"]
    assert all_v2[("V1", "R01")]["status"] == "open"

    v1_list = {(i["element_guid"], i["rule_id"]): i for i in client.get("/api/issues", params={"snapshot_id": s1["id"]}).json()}
    r04 = v1_list[("W1", "R04")]
    # status = estado dentro de v1 (abierto); fixed_by/resolved_at son la historia global del issue
    assert r04["status"] == "open" and r04["fixed_by"] == "manual" and r04["resolved_at"]
    assert v1_list[("C1", "R05")]["fixed_by"] == "one_click"  # no se pisa

    # filtros
    assert {i["rule_id"] for i in client.get("/api/issues", params={"status": "open", "discipline": "EST"}).json()} == {"R02"}
    assert len(client.get("/api/issues", params={"rule_id": "R02"}).json()) == 2
    assert len(client.get("/api/issues", params={"element_guid": "V1"}).json()) == 1

    # dismissed
    d = client.patch(f"/api/issues/{all_v2[(None, 'R06')]['id']}", json={"status": "dismissed"}).json()
    assert d["status"] == "dismissed"
    assert client.get(f"/api/snapshots/{s2['id']}").json()["open_issue_count"] == 3


def test_regression_reopens_issue(client):
    client.post("/api/snapshots", json=snapshot_body("v1"))
    client.post("/api/snapshots", json=snapshot_body("v2", issues=[]))
    v1 = client.get("/api/issues", params={"snapshot_id": 1}).json()
    assert v1 and all(i["status"] == "open" and i["resolved_at"] for i in v1)
    assert client.get("/api/issues", params={"snapshot_id": 2}).json() == []
    client.post("/api/snapshots", json=snapshot_body("v3"))
    issues = client.get("/api/issues").json()
    assert len(issues) == 5 and all(i["status"] == "open" and i["fixed_by"] is None for i in issues)


def test_cde_gate(client):
    s1 = client.post("/api/snapshots", json=snapshot_body("v1")).json()
    for state in ("SHARED", "PUBLISHED"):
        r = client.patch(f"/api/snapshots/{s1['id']}/cde-state", json={"cde_state": state})
        assert r.status_code == 409 and "error" in r.json()["detail"]
    assert client.patch(f"/api/snapshots/{s1['id']}/cde-state", json={"cde_state": "ARCHIVED"}).status_code == 200
    assert client.patch("/api/snapshots/999/cde-state", json={"cde_state": "WIP"}).status_code == 404

    warnings_only = [{"element_guid": "W1", "rule_id": "R04", "severity": "warning", "message": "o", "related_guid": "B1"}]
    s2 = client.post("/api/snapshots", json=snapshot_body("v2", issues=warnings_only)).json()
    r = client.patch(f"/api/snapshots/{s2['id']}/cde-state", json={"cde_state": "SHARED"})
    assert r.status_code == 200 and r.json()["cde_state"] == "SHARED"
    assert client.patch(f"/api/snapshots/{s2['id']}/cde-state", json={"cde_state": "PUBLISHED"}).status_code == 200

    lst = client.get("/api/snapshots").json()
    assert [s["version_label"] for s in lst] == ["v2", "v1"]


def test_cde_gate_after_patch(client):
    s1 = client.post("/api/snapshots", json=snapshot_body("v1")).json()
    for i in client.get("/api/issues", params={"status": "open"}).json():
        if i["severity"] == "error":
            client.patch(f"/api/issues/{i['id']}", json={"status": "fixed", "fixed_by": "one_click"})
    assert client.patch(f"/api/snapshots/{s1['id']}/cde-state", json={"cde_state": "SHARED"}).status_code == 200


def test_feedback_and_thread(client):
    client.post("/api/snapshots", json=snapshot_body("v1"))
    issue = next(i for i in client.get("/api/issues").json() if i["element_guid"] == "W2")
    r = client.post("/api/feedback", json={"element_guid": "W2", "rule_id": "R02", "issue_id": issue["id"],
                                           "reason": "no_encuentro_codigo", "comment": "no sé"})
    assert r.status_code == 201 and r.json()["id"] and r.json()["created_at"].endswith("Z")
    assert client.post("/api/feedback", json={"element_guid": "W2", "rule_id": "R02", "reason": "x"}).status_code == 422
    assert client.post("/api/feedback", json={"element_guid": "W2", "rule_id": "R02", "reason": "otro",
                                              "comment": "a" * 501}).status_code == 422
    assert len(client.get("/api/feedback", params={"rule_id": "R02"}).json()) == 1
    assert client.get("/api/feedback", params={"element_guid": "ZZ"}).json() == []

    client.post("/api/snapshots", json=snapshot_body("v2", issues=[]))
    t = client.get("/api/elements/W2/thread").json()
    assert t["guid"] == "W2" and t["latest"]["guid"] == "W2"
    assert [e["kind"] for e in t["events"]] == ["issue_opened", "feedback", "issue_fixed"]
    assert t["events"][0]["issue"]["rule_id"] == "R02"
    assert t["events"][1]["feedback"]["reason"] == "no_encuentro_codigo"
    assert client.get("/api/elements/NOPE/thread").status_code == 404


def test_r05_one_issue_per_parameter(client):
    def r05(param):
        return {"element_guid": "C1", "rule_id": "R05", "severity": "warning",
                "message": f'Falta el parámetro "{param}" exigido por el LOIN.'}
    client.post("/api/snapshots", json=snapshot_body("v1", issues=[r05("BIM_Material"), r05("BIM_Resistencia_fc")]))
    v1 = client.get("/api/issues").json()
    assert len(v1) == 2 and all(i["status"] == "open" for i in v1)
    # v2: el modelador completó BIM_Material; sigue faltando BIM_Resistencia_fc
    client.post("/api/snapshots", json=snapshot_body("v2", issues=[r05("BIM_Resistencia_fc")]))
    by_msg = {i["message"]: i for i in client.get("/api/issues", params={"snapshot_id": 1}).json()}
    assert by_msg[r05("BIM_Material")["message"]]["resolved_at"]
    v2 = client.get("/api/issues", params={"snapshot_id": 2}).json()
    assert [i["message"] for i in v2] == [r05("BIM_Resistencia_fc")["message"]]
    still = by_msg[r05("BIM_Resistencia_fc")["message"]]
    assert still["status"] == "open" and still["snapshot_id"] == 2
    assert client.get("/api/snapshots/2").json()["open_issue_count"] == 1


def test_contract_020_doc_feedback_and_stats_totals(client):
    client.post("/api/snapshots", json=snapshot_body("v1"))
    r = client.post("/api/feedback", json={"element_guid": None, "rule_id": "R06", "reason": "regla_no_aplica"})
    assert r.status_code == 201 and r.json()["element_guid"] is None
    st = client.get("/api/stats").json()
    # 2 errores + 3 warnings; el R06 de documento (sin disciplina) cuenta en el total
    assert (st["open_errors"], st["open_warnings"]) == (2, 3)
    assert sum(d["open_warnings"] for d in st["by_discipline"]) == 2
