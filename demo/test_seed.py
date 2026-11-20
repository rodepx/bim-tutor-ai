"""Pruebas del simulador del plugin (sin red).

Ejecutar:  backend\\.venv\\Scripts\\python.exe -m pytest demo -q
"""
import json
import re
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import seed  # noqa: E402

RULE_IDS = [f"R0{i}" for i in range(1, 8)]

# Requeridos según contracts/openapi.yaml (respaldo si no hay pyyaml/jsonschema)
REQ = {
    "SnapshotCreate": ["project_code", "file_name", "version_label", "cde_state", "rules_version", "elements", "issues"],
    "Element": ["guid", "category", "discipline", "type_name"],
    "IssueCreate": ["rule_id", "severity", "message"],
    "FeedbackCreate": ["element_guid", "rule_id", "reason"],
}


@pytest.fixture(scope="module")
def v1():
    return seed.build_snapshot("v1")


@pytest.fixture(scope="module")
def v2():
    return seed.build_snapshot("v2")


@pytest.fixture(scope="module")
def feedback():
    return seed.build_feedback()


@pytest.fixture(scope="module")
def spec():
    yaml = pytest.importorskip("yaml")
    return yaml.safe_load((ROOT / "contracts" / "openapi.yaml").read_text(encoding="utf-8"))


def test_dry_run_writes_files(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(seed, "OUT", tmp_path)
    assert seed.main(["--dry-run"]) == 0
    for name in ("v1.json", "v2.json", "feedback.json"):
        assert json.loads((tmp_path / name).read_text(encoding="utf-8"))
    assert "R01" in capsys.readouterr().out


def test_v1_has_every_rule(v1):
    found = {i["rule_id"] for i in v1["issues"]}
    assert set(RULE_IDS) <= found, f"faltan reglas en v1: {set(RULE_IDS) - found}"


def test_v1_r06_and_r04_shape(v1):
    r06 = [i for i in v1["issues"] if i["rule_id"] == "R06"]
    assert r06 and all(i["element_guid"] is None for i in r06)
    r04 = [i for i in v1["issues"] if i["rule_id"] == "R04"]
    assert r04 and all(i["related_guid"] for i in r04)
    guids = {e["guid"] for e in v1["elements"]}
    assert all(i["related_guid"] in guids for i in r04)


def test_messages_have_no_unfilled_placeholders(v1, v2):
    for i in v1["issues"] + v2["issues"]:
        assert not re.search(r"\{\w+\}", i["message"]), i["message"]


def test_v2_has_no_errors_but_some_warnings(v2):
    sev = [i["severity"] for i in v2["issues"]]
    assert "error" not in sev
    assert "warning" in sev


def test_v2_file_name_iso19650(v2):
    pattern = next(r for r in seed.load_rules()["rules"] if r["id"] == "R06")["params"]["pattern"]
    assert re.fullmatch(pattern, v2["file_name"])


def test_element_count_and_unique_guids(v1, v2):
    for snap in (v1, v2):
        assert 40 <= len(snap["elements"]) <= 60
        guids = [e["guid"] for e in snap["elements"]]
        assert len(guids) == len(set(guids))


def test_guids_stable_between_versions(v1, v2):
    common = {e["guid"] for e in v1["elements"]} & {e["guid"] for e in v2["elements"]}
    assert len(common) >= 50  # mismo UniqueId = mismo elemento → hilo y diff funcionan
    assert seed.build_snapshot("v1")["elements"][0]["guid"] == v1["elements"][0]["guid"]


def test_budget_diff_visible(v1, v2):
    g1 = {e["guid"]: e for e in v1["elements"]}
    g2 = {e["guid"]: e for e in v2["elements"]}
    assert set(g2) - set(g1), "v2 debe agregar elementos"
    assert set(g1) - set(g2), "v2 debe quitar elementos"
    keys = ("type_name", "classification_code", "volume_m3", "area_m2", "length_m")
    assert any(any(g1[k][f] != g2[k][f] for f in keys) for k in set(g1) & set(g2))


def test_required_fields_manual(v1, v2, feedback):
    for snap in (v1, v2):
        assert all(k in snap for k in REQ["SnapshotCreate"])
        for e in snap["elements"]:
            assert all(e.get(k) is not None for k in REQ["Element"]), e
            assert e["discipline"] in ("ARQ", "EST", "MEP")
            for k in ("volume_m3", "area_m2", "length_m"):
                assert e[k] is None or e[k] >= 0
        for i in snap["issues"]:
            assert all(i.get(k) is not None for k in REQ["IssueCreate"]), i
    for f in feedback:
        assert all(f.get(k) is not None for k in REQ["FeedbackCreate"])
        assert len(f.get("comment") or "") <= 500


def test_payloads_match_openapi(spec, v1, v2, feedback):
    jsonschema = pytest.importorskip("jsonschema")

    def validator(name):
        root = {"$ref": f"#/components/schemas/{name}", "components": spec["components"]}
        return jsonschema.Draft202012Validator(root)

    snap_v = validator("SnapshotCreate")
    for snap in (v1, v2):
        errors = list(snap_v.iter_errors(snap))
        assert not errors, errors[0].message
    fb_v = validator("FeedbackCreate")
    for f in feedback:
        errors = list(fb_v.iter_errors({**f, "issue_id": None}))
        assert not errors, errors[0].message
    # Los required del contrato coinciden con el respaldo manual
    for name, req in REQ.items():
        assert set(spec["components"]["schemas"][name]["required"]) == set(req)


def test_v2_codes_exist_and_are_budgetable(v2):
    uniclass = seed.load_uniclass()
    mapped = {r["uniclass_code"] for r in seed.load_mapping()}
    for e in v2["elements"]:
        code = e["classification_code"]
        assert code, f"{e['type_name']} sin código en v2"
        assert code in uniclass, code
        assert e["category"] in uniclass[code]["categories"], (code, e["category"])
        assert code in mapped, f"{code} no tiene partida en mapeo_partidas.csv"


def test_feedback_targets_v1_issues(v1, feedback):
    keys = {(i["element_guid"], i["rule_id"]) for i in v1["issues"]}
    reasons = {f["reason"] for f in feedback}
    assert 4 <= len(feedback) <= 6 and len(reasons) >= 4
    for f in feedback:
        assert (f["element_guid"], f["rule_id"]) in keys, f
