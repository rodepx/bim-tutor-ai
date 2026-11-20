"""Carga de data/rules.json, data/uniclass_subset.csv y data/mapeo_partidas.csv (cacheado)."""
import csv
import json
from functools import lru_cache

from jsonschema import Draft202012Validator

from app.config import CONTRACTS_DIR, DATA_DIR


@lru_cache
def load_rules() -> dict:
    rules = json.loads((DATA_DIR / "rules.json").read_text(encoding="utf-8"))
    schema = json.loads((CONTRACTS_DIR / "rules.schema.json").read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(schema).iter_errors(rules), key=lambda e: list(e.path))
    if errors:
        msgs = "; ".join(f"{'/'.join(map(str, e.path)) or '<root>'}: {e.message}" for e in errors)
        raise RuntimeError(f"data/rules.json no cumple contracts/rules.schema.json: {msgs}")
    return rules


def rules_by_id() -> dict[str, dict]:
    return {r["id"]: r for r in load_rules()["rules"]}


def rule_name(rule_id: str) -> str:
    r = rules_by_id().get(rule_id)
    return r["name"] if r else rule_id


def _read_csv(name: str) -> list[dict]:
    with open(DATA_DIR / name, encoding="utf-8-sig", newline="") as f:
        return [{k.strip(): (v or "").strip() for k, v in row.items()} for row in csv.DictReader(f)]


@lru_cache
def load_uniclass() -> list[dict]:
    out = []
    for row in _read_csv("uniclass_subset.csv"):
        out.append({
            "code": row["code"],
            "title_es": row["title_es"],
            "title_en": row.get("title_en") or None,
            "table": row["table"],
            "revit_categories": [c.strip() for c in row["revit_categories"].split(";") if c.strip()],
            "estado": row.get("estado", ""),
        })
    return out


def uniclass_public(category: str | None = None) -> list[dict]:
    """Filas en forma UniclassCode (sin columnas internas)."""
    rows = load_uniclass()
    if category:
        rows = [r for r in rows if category in r["revit_categories"]]
    return [{k: r[k] for k in ("code", "title_es", "title_en", "table", "revit_categories")} for r in rows]


def uniclass_by_code() -> dict[str, dict]:
    return {r["code"]: r for r in load_uniclass()}


@lru_cache
def load_mapping() -> list[dict]:
    out = []
    for row in _read_csv("mapeo_partidas.csv"):
        out.append({
            "uniclass_code": row["uniclass_code"],
            "partida_codigo": row["partida_codigo"],
            "descripcion": row["partida_descripcion"],
            "unidad": row["unidad"],
            "magnitud_fuente": row["magnitud_fuente"],
            "factor": float(row["factor"]),
            "precio_unitario": float(row["precio_unitario_pen"]),
            "estado": row.get("estado", ""),
        })
    return out


def mapping_by_code() -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for row in load_mapping():
        out.setdefault(row["uniclass_code"], []).append(row)
    return out
