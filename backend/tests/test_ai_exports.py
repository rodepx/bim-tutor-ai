import csv
import io
import zipfile
import xml.etree.ElementTree as ET

from openpyxl import load_workbook

from app.services.exports import ifc_guid_from_unique_id
from app.services.stats import compute_facts
from conftest import el, snapshot_body

FACT_KEYS = {
    "conformance_pct", "open_errors", "open_warnings", "top_rule_id", "top_rule_name", "top_rule_open_count",
    "budget_total", "unbudgeted_count", "unbudgeted_sin_codigo", "overlap_warnings", "delta_total", "delta_pct",
    "feedback_top_reason", "feedback_top_count", "cde_state", "can_move_to_shared",
}


def test_ai_explain(client):
    r = client.post("/api/ai/explain", json={"rule_id": "R02", "element": el("W2", "OST_Walls")})
    assert r.status_code == 200 and r.json()["rule_id"] == "R02" and r.json()["mode"] == "mock"
    assert client.post("/api/ai/explain", json={"rule_id": "R99"}).status_code == 404


def test_ai_suggest_filters_candidates(client, monkeypatch):
    r = client.post("/api/ai/suggest-classification", json={"element": el("W2", "OST_Walls")}).json()
    codes = {c["code"] for c in r["candidates"]}
    assert codes == {"Ss_20_05_65", "Ss_25_10_20", "Ss_25_10_50", "Ss_25_10_30"}
    assert r["suggested_code"] in codes

    from app.routers import ai as ai_router
    monkeypatch.setattr(ai_router, "suggest_classification", lambda e, c: {
        "element_guid": e["guid"], "candidates": c, "suggested_code": "Ss_20_10_10", "reason": "x", "mode": "mock"})
    r = client.post("/api/ai/suggest-classification", json={"element": el("W2", "OST_Walls")}).json()
    assert r["suggested_code"] is None  # fuera de candidates


def test_facts_and_recommendations(client):
    client.post("/api/snapshots", json=snapshot_body("v1"))
    client.post("/api/feedback", json={"element_guid": "W2", "rule_id": "R02", "reason": "no_encuentro_codigo"})
    from app import db, models
    with db.SessionLocal() as s:
        snap = s.get(models.Snapshot, 1)
        f = compute_facts(s, snap)
    assert FACT_KEYS <= f.keys()
    assert f["open_errors"] == 2 and f["open_warnings"] == 3 and f["top_rule_id"] == "R02"
    assert f["top_rule_open_count"] == 2 and f["budget_total"] == 4719.52 and f["unbudgeted_sin_codigo"] == 2
    assert f["delta_total"] is None and f["delta_pct"] is None
    assert f["feedback_top_reason"] == "no_encuentro_codigo" and f["can_move_to_shared"] is False

    client.post("/api/snapshots", json=snapshot_body("v2", issues=[]))
    with db.SessionLocal() as s:
        f2 = compute_facts(s, s.get(models.Snapshot, 2))
    assert f2["delta_total"] == 0.0 and f2["delta_pct"] == 0.0 and f2["previous_snapshot_id"] == 1

    recs = client.get("/api/ai/recommendations").json()
    assert recs[0]["id"] == "rec1" and recs[0]["facts"]["open_errors"] == 0


def test_ifc_guid():
    # 22 caracteres del alfabeto IFC; formato inválido → None
    g = ifc_guid_from_unique_id("60f91daf-3dd7-4283-a86d-24137b73f3da-0001fd0b")
    assert g and len(g) == 22 and g[0] in "0123"
    assert ifc_guid_from_unique_id("W1") is None


def test_export_bcf(client):
    body = snapshot_body(elements=[el("60f91daf-3dd7-4283-a86d-24137b73f3da-0001fd0b", "OST_Walls")],
                         issues=[{"element_guid": "60f91daf-3dd7-4283-a86d-24137b73f3da-0001fd0b",
                                  "rule_id": "R02", "severity": "error", "message": "sin <código>"},
                                 {"element_guid": None, "rule_id": "R06", "severity": "warning", "message": "x"}])
    client.post("/api/snapshots", json=body)
    r = client.get("/api/export/bcf")
    assert r.status_code == 200 and r.headers["content-type"] == "application/octet-stream"
    z = zipfile.ZipFile(io.BytesIO(r.content))
    names = z.namelist()
    assert "bcf.version" in names
    assert ET.fromstring(z.read("bcf.version")).get("VersionId") == "2.1"
    markups = [n for n in names if n.endswith("/markup.bcf")]
    assert len(markups) == 2
    titles = {ET.fromstring(z.read(m)).find("Topic/Title").text for m in markups}
    assert "R02 - Elemento sin código Uniclass" in titles
    vps = [n for n in names if n.endswith("/viewpoint.bcfv")]
    assert len(vps) == 1
    comp = ET.fromstring(z.read(vps[0])).find("Components/Selection/Component")
    assert comp.find("AuthoringToolId").text == "60f91daf-3dd7-4283-a86d-24137b73f3da-0001fd0b"
    assert len(comp.get("IfcGuid")) == 22


def test_export_4d(client):
    client.post("/api/snapshots", json=snapshot_body())
    r = client.get("/api/export/4d.csv")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    rows = list(csv.reader(io.StringIO(r.text)))
    assert rows[0] == ["guid", "category", "type_name", "level", "uniclass_code", "partida_codigo", "quantity", "unit",
                       "fase_sugerida"]
    assert len(rows) == 11  # cabecera + 10 elementos únicos
    by_guid = {r[0]: r for r in rows[1:]}
    assert by_guid["C1"][5:] == ["OE.2.3.6.1", "0.48", "m3", "estructura"]
    assert by_guid["D1"][5:] == ["OE.3.9.1.1", "1.0", "und", "acabados"]
    assert by_guid["W2"][8] == "albanileria" and by_guid["W1"][8] == "estructura"


def test_export_cobie(client):
    client.post("/api/snapshots", json=snapshot_body())
    r = client.get("/api/export/cobie.xlsx")
    assert r.status_code == 200
    wb = load_workbook(io.BytesIO(r.content))
    assert wb.sheetnames == ["Contact", "Facility", "Floor", "Type", "Component"]
    assert wb["Component"].max_row == 11
    assert wb["Floor"]["A2"].value == "Nivel 1"


def test_exports_404_without_snapshot(client):
    for p in ("/api/export/bcf", "/api/export/4d.csv", "/api/export/cobie.xlsx"):
        assert client.get(p).status_code == 404
