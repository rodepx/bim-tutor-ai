#!/usr/bin/env python3
"""
seed.py — Simula el plugin Revit del Agente Profesor BIM sin Revit.

Genera un edificio de concreto de 2 niveles (~56 elementos), le siembra errores,
ejecuta un port en Python de las reglas de data/rules.json y envía dos versiones
(v1 WIP sucia, v2 corregida) + feedback al backend.

Uso:
    python demo/seed.py                       # envía a http://localhost:8000/api
    python demo/seed.py --base http://host:8000/api
    python demo/seed.py --dry-run             # sin red: escribe demo/out/*.json

Solo usa la librería estándar.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import urllib.error
import urllib.request
import uuid
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = Path(__file__).resolve().parent / "out"

PROJECT_CODE = "HKT"
FILE_V1 = "Edificio Final v1 (copia)"          # viola R06
FILE_V2 = "HKT-EQP-ZZ-ZZ-M3-S-0001"            # cumple R06
AUTHOR = "seed.py (simulador del plugin)"
NS = uuid.UUID("6f1c2a7e-0b5d-4f0e-9a51-48b1d3c0e7a2")  # namespace fijo → guids deterministas


# ---------------------------------------------------------------------------
# Datos del repo
# ---------------------------------------------------------------------------
def load_rules() -> dict:
    with open(DATA / "rules.json", encoding="utf-8-sig") as f:
        return json.load(f)


def load_uniclass() -> dict[str, dict]:
    with open(DATA / "uniclass_subset.csv", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    return {
        r["code"].strip(): {**r, "categories": [c.strip() for c in r["revit_categories"].split(";") if c.strip()]}
        for r in rows
    }


def load_mapping() -> list[dict]:
    with open(DATA / "mapeo_partidas.csv", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


# ---------------------------------------------------------------------------
# Generador del modelo
# ---------------------------------------------------------------------------
def _guid(key: str, element_id: int) -> str:
    """Imita un UniqueId de Revit: <GUID>-<ElementId en 8 hex>."""
    return f"{uuid.uuid5(NS, key)}-{element_id:08x}"


def _el(key, category, family, type_name, code, level, volume=None, area=None, length=None, params=None):
    eid = 300000 + (uuid.uuid5(NS, key).int % 600000)  # estable por key
    return {
        "_key": key,
        "guid": _guid(key, eid),
        "element_id": eid,
        "category": category,
        "family_name": family,
        "type_name": type_name,
        "classification_code": code,
        "level": level,
        "volume_m3": None if volume is None else round(volume, 3),
        "area_m2": None if area is None else round(area, 3),
        "length_m": None if length is None else round(length, 3),
        "parameters": dict(params or {}),
    }


CA = {"BIM_Material": "Concreto armado", "BIM_Resistencia_fc": "210"}
LAD = {"BIM_Material": "Albañilería de ladrillo King Kong"}
DRY = {"BIM_Material": "Drywall (placa de yeso + perfiles)"}


def base_model() -> dict[str, dict]:
    """Modelo limpio (todo cumple). Las versiones aplican defectos/cambios encima."""
    els: list[dict] = []
    xs = {"A": 0.0, "B": 5.0, "C": 10.0}
    ys = {"1": 0.0, "2": 4.5}
    levels = ["Nivel 1", "Nivel 2"]
    h = 3.0  # piso a piso

    # Zapatas 1.50 x 1.50 x 0.60
    for gx in xs:
        for gy in ys:
            els.append(_el(f"ZAP-{gx}{gy}", "OST_StructuralFoundation", "Zapata aislada",
                           "ZAP_CA_150x150x60_FC210", "Ss_20_05_15", "Nivel 1",
                           volume=1.5 * 1.5 * 0.6, area=1.5 * 1.5, params=CA))
    # Columnas 40x40, h = 3.00
    for lv_i, lv in enumerate(levels, 1):
        for gx in xs:
            for gy in ys:
                els.append(_el(f"COL-N{lv_i}-{gx}{gy}", "OST_StructuralColumns", "Columna rectangular CA",
                               "COL_CA_40x40_FC210", "Ss_20_10_10", lv,
                               volume=0.4 * 0.4 * h, length=h, params=CA))
    # Vigas 25x50 — luz libre: 4.60 (x) / 4.10 (y)
    for lv_i in (1, 2):
        lv = {1: "Nivel 2", 2: "Techo"}[lv_i]  # la viga pertenece al nivel que soporta
        for gy in ys:
            for a, b in (("A", "B"), ("B", "C")):
                L = 5.0 - 0.4
                els.append(_el(f"VIG-N{lv_i}-X{gy}-{a}{b}", "OST_StructuralFraming", "Viga rectangular CA",
                               "VIG_CA_25x50_FC210", "Ss_20_10_20", lv,
                               volume=0.25 * 0.5 * L, length=L, params=CA))
        for gx in xs:
            L = 4.5 - 0.4
            els.append(_el(f"VIG-N{lv_i}-Y{gx}", "OST_StructuralFraming", "Viga rectangular CA",
                           "VIG_CA_25x50_FC210", "Ss_20_10_20", lv,
                           volume=0.25 * 0.5 * L, length=L, params=CA))
    # Losas: aligerada (entrepiso) y maciza (techo); área a caras exteriores 10.40 x 4.90
    A = 10.4 * 4.9
    els.append(_el("LOS-N2-ALIG", "OST_Floors", "Suelo", "LOS_ALIG_e20", "Ss_30_10_35", "Nivel 2",
                   volume=A * 0.0875, area=A, params={"BIM_Material": "Concreto armado + ladrillo de techo"}))
    els.append(_el("LOS-TECHO-MAC", "OST_Floors", "Suelo", "LOS_MAC_e20_FC210", "Ss_30_10_30", "Techo",
                   volume=A * 0.20, area=A, params=CA))
    # Placas (eje C, entre columnas) e=25, h=2.50 bajo viga
    for lv_i, lv in enumerate(levels, 1):
        L, H = 4.1, 2.5
        els.append(_el(f"PLA-N{lv_i}-C", "OST_Walls", "Muro básico", "MUR_CA_e25_FC210", "Ss_25_10_20", lv,
                       volume=L * H * 0.25, area=L * H, length=L, params=CA))
    # Muros de ladrillo e=15, h=2.50 (bajo viga)
    for lv_i, lv in enumerate(levels, 1):
        for key, L in (("1-AB", 4.6), ("1-BC", 4.6), ("2-AB", 4.6)):
            H = 2.5
            els.append(_el(f"LAD-N{lv_i}-{key}", "OST_Walls", "Muro básico", "MUR_LAD_e15", "Ss_25_10_50", lv,
                           volume=L * H * 0.15, area=L * H, length=L, params=LAD))
    # Tabiques drywall e=15, h=2.80 (hasta losa)
    for lv_i, lv in enumerate(levels, 1):
        for t in (1, 2):
            L, H = 4.1, 2.8
            els.append(_el(f"DRY-N{lv_i}-T{t}", "OST_Walls", "Muro básico", "MUR_DRY_e15", "Ss_25_10_30", lv,
                           volume=L * H * 0.15, area=L * H, length=L, params=DRY))
    # Puertas 0.90 x 2.10
    for lv_i, lv in enumerate(levels, 1):
        for p in (1, 2):
            els.append(_el(f"PTA-N{lv_i}-P{p}", "OST_Doors", "Puerta contraplacada", "PTA_MAD_090x210",
                           "Ss_25_30_20", lv, area=0.9 * 2.1, params={"BIM_Material": "Madera contraplacada"}))
    # Ventanas 1.20 x 1.50
    for lv_i, lv in enumerate(levels, 1):
        for v in (1, 2, 3):
            els.append(_el(f"VEN-N{lv_i}-V{v}", "OST_Windows", "Ventana corrediza", "VEN_ALU_120x150",
                           "Ss_25_30_95", lv, area=1.2 * 1.5, params={"BIM_Material": "Aluminio + vidrio 6 mm"}))
    return {e["_key"]: e for e in els}


def _ladrillo_full_height(e: dict) -> None:
    """Muro modelado hasta el techo (3.00 m): invade la viga → superposición."""
    L = e["length_m"]
    e["area_m2"] = round(L * 3.0, 3)
    e["volume_m3"] = round(L * 3.0 * 0.15, 3)


def build_v1() -> tuple[list[dict], list[tuple[str, str, bool]]]:
    m = base_model()
    # R01 nombres genéricos (+ R02/R05 en el mismo muro, como pasa con la plantilla)
    w = m["LAD-N1-1-AB"]
    w["type_name"] = "Muro básico - Genérico 200 mm"
    w["classification_code"] = None
    w["parameters"].pop("BIM_Material")
    w["volume_m3"] = round(w["length_m"] * 2.5 * 0.20, 3)
    m["COL-N2-C2"]["type_name"] = "COL_CA_40x40_FC210 2"
    m["PTA-N2-P1"]["type_name"] = "Default"
    m["VEN-N1-V3"]["type_name"] = "Copia de VEN_ALU_120x150"
    # R02 sin código
    for k in ("DRY-N2-T1", "VEN-N2-V1", "ZAP-B1"):
        m[k]["classification_code"] = None
    # R03 inexistente / categoría equivocada
    m["LAD-N2-2-AB"]["classification_code"] = "Ss_25_10_99"      # no existe
    m["COL-N1-A1"]["classification_code"] = "Ss_20_10_20"        # es de vigas
    m["PTA-N1-P2"]["classification_code"] = "Ss_25_30_95"        # es de ventanas
    # R05 LOIN faltante
    for k in ("COL-N1-B1", "COL-N1-B2"):
        m[k]["parameters"].pop("BIM_Resistencia_fc")
    m["LOS-N2-ALIG"]["parameters"].pop("BIM_Material")
    # R07 sin nivel
    m["VIG-N2-YB"]["level"] = None
    m["DRY-N1-T2"]["level"] = None
    # R04 muros hasta el techo que invaden vigas, sin unir
    _ladrillo_full_height(m["LAD-N1-2-AB"])
    _ladrillo_full_height(m["LAD-N2-1-BC"])
    overlaps = [
        (m["LAD-N1-2-AB"]["guid"], m["VIG-N1-X2-AB"]["guid"], False),
        (m["LAD-N2-1-BC"]["guid"], m["VIG-N2-X1-BC"]["guid"], False),
    ]
    return list(m.values()), overlaps


def build_v2() -> tuple[list[dict], list[tuple[str, str, bool]]]:
    m = base_model()
    # Superposición 1 corregida con "Unir geometría": Revit descuenta el volumen de la viga
    # (el muro queda con las magnitudes del modelo limpio). La 2 sigue abierta (warning).
    _ladrillo_full_height(m["LAD-N2-1-BC"])
    overlaps = [
        (m["LAD-N1-2-AB"]["guid"], m["VIG-N1-X2-AB"]["guid"], True),
        (m["LAD-N2-1-BC"]["guid"], m["VIG-N2-X1-BC"]["guid"], False),
    ]
    # Eliminado: la ventana duplicada ("Copia de ...")
    del m["VEN-N1-V3"]
    # Agregados: 2 tabiques y 1 ventana nuevos en Nivel 2 (uno sin material → R05 warning)
    for t in (3, 4):
        m[f"DRY-N2-T{t}"] = _el(f"DRY-N2-T{t}", "OST_Walls", "Muro básico", "MUR_DRY_e15", "Ss_25_10_30",
                                "Nivel 2", volume=3.2 * 2.8 * 0.15, area=3.2 * 2.8, length=3.2, params=DRY)
    m["DRY-N2-T4"]["parameters"].pop("BIM_Material")
    m["VEN-N2-V4"] = _el("VEN-N2-V4", "OST_Windows", "Ventana corrediza", "VEN_ALU_120x150", "Ss_25_30_95",
                         "Nivel 2", area=1.2 * 1.5, params={"BIM_Material": "Aluminio + vidrio 6 mm"})
    # Modificado: la losa aligerada crece por un volado de 1.00 m en el eje 2
    los = m["LOS-N2-ALIG"]
    los["area_m2"] = round(10.4 * 5.9, 3)
    los["volume_m3"] = round(10.4 * 5.9 * 0.0875, 3)
    return list(m.values()), overlaps


# ---------------------------------------------------------------------------
# Port en Python de las reglas del plugin
# ---------------------------------------------------------------------------
def _fmt(template: str, **values) -> str:
    return re.sub(r"\{(\w+)\}", lambda mo: str(values.get(mo.group(1), mo.group(0))), template)


def discipline_of(category: str, rules: dict) -> str | None:
    for disc, cats in rules["disciplines"].items():
        if category in cats:
            return disc
    return None


def _code_of(e: dict, rules: dict) -> str | None:
    code = e.get("classification_code")
    if not code:
        names = [rules["classification"]["parameter_name"], *rules["classification"]["fallback_parameter_names"]]
        for n in names:
            v = e.get("parameters", {}).get(n)
            if v:
                code = v
                break
    return code.strip() if isinstance(code, str) and code.strip() else None


def run_rules(elements: list[dict], file_name: str, overlaps, rules: dict, uniclass: dict) -> list[dict]:
    issues: list[dict] = []
    by_guid = {e["guid"]: e for e in elements}

    def add(rule, guid, message, related=None):
        issues.append({"element_guid": guid, "rule_id": rule["id"], "severity": rule["severity"],
                       "message": message, "related_guid": related})

    for rule in rules["rules"]:
        if not rule.get("enabled", True):
            continue
        check, p, scope = rule["check"], rule.get("params", {}), rule["scope"]
        cats = set(scope.get("categories", []))
        in_scope = [e for e in elements if e["category"] in cats]

        if check == "type_name_not_generic":
            pats = [re.compile(x, re.IGNORECASE) for x in p["forbidden_patterns"]]
            for e in in_scope:
                if any(px.search(e["type_name"]) for px in pats):
                    add(rule, e["guid"], _fmt(rule["message"], type_name=e["type_name"]))

        elif check == "classification_required":
            for e in in_scope:
                if _code_of(e, rules) is None:
                    add(rule, e["guid"], _fmt(rule["message"], parameter=rules["classification"]["parameter_name"]))

        elif check == "classification_exists":
            for e in in_scope:
                code = _code_of(e, rules)
                if code is None:
                    continue  # lo cubre classification_required
                row = uniclass.get(code)
                if row is None or e["category"] not in row["categories"]:
                    add(rule, e["guid"], _fmt(rule["message"], code=code, category=e["category"]))

        elif check == "required_parameters":
            for e in in_scope:
                req = p["parameters_by_category"].get(e["category"], [])
                for name in req:
                    if not (e.get("parameters", {}).get(name) or "").strip():
                        add(rule, e["guid"], _fmt(rule["message"], parameter=name))

        elif check == "level_required":
            for e in in_scope:
                if not e.get("level"):
                    add(rule, e["guid"], rule["message"])

        elif check == "no_overlap":
            for a, b, joined in overlaps:
                ea, eb = by_guid.get(a), by_guid.get(b)
                if not ea or not eb:
                    continue
                if {ea["category"], eb["category"]} != {p["category_a"], p["category_b"]}:
                    continue
                if joined and p.get("ignore_if_joined", True):
                    continue
                add(rule, a, _fmt(rule["message"], other_guid=b), related=b)

        elif check == "file_naming":
            stem = re.sub(r"\.rvt$", "", file_name, flags=re.IGNORECASE)
            if not re.fullmatch(p["pattern"], stem):
                add(rule, None, _fmt(rule["message"], file_name=file_name))
    return issues


# ---------------------------------------------------------------------------
# Payloads
# ---------------------------------------------------------------------------
def to_payload_element(e: dict, rules: dict) -> dict:
    out = {k: v for k, v in e.items() if not k.startswith("_")}
    out["discipline"] = discipline_of(e["category"], rules)
    params = dict(out["parameters"])
    params[rules["classification"]["parameter_name"]] = e.get("classification_code")
    out["parameters"] = {k: (None if v is None else str(v)) for k, v in params.items()}
    return out


def build_snapshot(version: str) -> dict:
    rules, uniclass = load_rules(), load_uniclass()
    if version == "v1":
        elements, overlaps = build_v1()
        file_name = FILE_V1
    else:
        elements, overlaps = build_v2()
        file_name = FILE_V2
    issues = run_rules(elements, file_name, overlaps, rules, uniclass)
    return {
        "project_code": PROJECT_CODE,
        "file_name": file_name,
        "version_label": version,
        "cde_state": "WIP",
        "rules_version": rules["version"],
        "author": AUTHOR,
        "elements": [to_payload_element(e, rules) for e in elements],
        "issues": issues,
    }


def _guid_by_key(key: str) -> str:
    m = base_model()
    return m[key]["guid"]


def build_feedback() -> list[dict]:
    """Respuestas a la microencuesta "No pude, ¿por qué?" sobre issues de v1."""
    g = _guid_by_key
    return [
        {"element_guid": g("LAD-N2-2-AB"), "rule_id": "R03", "reason": "no_encuentro_codigo",
         "comment": "No sé qué código Uniclass usar para un muro de ladrillo tarrajeado.", "author": "Modelador ARQ"},
        {"element_guid": g("LAD-N1-2-AB"), "rule_id": "R04", "reason": "no_entiendo_regla",
         "comment": "¿Por qué importa si el muro toca la viga? En el plano se ve bien.", "author": "Modelador ARQ"},
        {"element_guid": g("COL-N1-B1"), "rule_id": "R05", "reason": "falta_informacion",
         "comment": "Estructuras todavía no define el f'c de las columnas del eje B.", "author": "Modelador EST"},
        {"element_guid": g("COL-N1-B2"), "rule_id": "R05", "reason": "falta_informacion",
         "comment": "Mismo caso: falta el f'c en el plano de estructuras.", "author": "Modelador EST"},
        {"element_guid": g("PTA-N2-P1"), "rule_id": "R01", "reason": "regla_no_aplica",
         "comment": "Es una familia del fabricante; no quiero romper su catálogo renombrando el tipo.", "author": "Modelador ARQ"},
        {"element_guid": g("VIG-N2-YB"), "rule_id": "R07", "reason": "error_del_plugin",
         "comment": "La viga tiene nivel de referencia 'Techo' pero el panel dice que no tiene nivel.", "author": "Modelador EST"},
    ]


# ---------------------------------------------------------------------------
# Presupuesto local (solo para el resumen; el oficial lo calcula el backend)
# ---------------------------------------------------------------------------
def local_budget(snapshot: dict) -> tuple[float, int]:
    uniclass, mapping = load_uniclass(), load_mapping()
    total, unbudgeted = 0.0, 0
    for e in snapshot["elements"]:
        code = e.get("classification_code")
        rows = [r for r in mapping if r["uniclass_code"] == code]
        if not code or code not in uniclass or e["category"] not in uniclass[code]["categories"] or not rows:
            unbudgeted += 1
            continue
        for r in rows:
            src = r["magnitud_fuente"]
            mag = 1.0 if src == "count" else e.get(src)
            if mag is None:
                continue
            qty = mag * float(r["factor"])
            total += round(qty * float(r["precio_unitario_pen"]), 2)
    return round(total, 2), unbudgeted


def summarize(snap: dict) -> str:
    by_rule = Counter(i["rule_id"] for i in snap["issues"])
    by_sev = Counter(i["severity"] for i in snap["issues"])
    total, unb = local_budget(snap)
    lines = [
        f"  {snap['version_label']}: archivo '{snap['file_name']}', {len(snap['elements'])} elementos, "
        f"{len(snap['issues'])} issues (errores {by_sev.get('error', 0)}, avisos {by_sev.get('warning', 0)})",
        "    por regla: " + (", ".join(f"{r}={by_rule[r]}" for r in sorted(by_rule)) or "ninguno"),
        f"    presupuesto estimado local: S/ {total:,.2f} — elementos no presupuestados: {unb}",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Red
# ---------------------------------------------------------------------------
class BackendError(Exception):
    def __init__(self, status: int, body: str):
        super().__init__(f"HTTP {status}: {body}")
        self.status, self.body = status, body


def http(method: str, url: str, body=None, timeout=15):
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode("utf-8")
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as ex:
        raise BackendError(ex.code, ex.read().decode("utf-8", "replace")[:500]) from None


def run_online(base: str, v1: dict, v2: dict, feedback: list[dict]) -> int:
    base = base.rstrip("/")
    print(f"\n→ Conectando a {base} ...")
    try:
        h = http("GET", f"{base}/health", timeout=5)
        print(f"  backend OK (versión {h.get('version')}, IA en modo {h.get('llm_mode')})")
    except (urllib.error.URLError, ConnectionError, TimeoutError, OSError) as ex:
        print(f"\n✗ No se pudo conectar al backend en {base} ({ex}).")
        print("  ¿Está levantado? Desde backend/:  .venv\\Scripts\\python -m uvicorn app.main:app --port 8000")
        print("  O usa el modo sin red:  python demo/seed.py --dry-run")
        return 2
    except BackendError as ex:
        print(f"\n✗ /health respondió con error: {ex}")
        return 2

    try:
        s1 = http("POST", f"{base}/snapshots", v1)
        print(f"✓ v1 enviada: snapshot #{s1['id']} ({s1['element_count']} elementos, "
              f"{s1['open_issue_count']} issues abiertos, estado {s1['cde_state']})")

        issues = http("GET", f"{base}/issues?snapshot_id={s1['id']}&status=open") or []
        idx = {(i.get("element_guid"), i["rule_id"]): i["id"] for i in issues}

        ok = 0
        for fb in feedback:
            body = {**fb, "issue_id": idx.get((fb["element_guid"], fb["rule_id"]))}
            try:
                http("POST", f"{base}/feedback", body)
                ok += 1
            except BackendError as ex:
                print(f"  ! feedback rechazado ({fb['rule_id']}): {ex}")
        print(f"✓ {ok}/{len(feedback)} respuestas de microencuesta enviadas")

        zap = _guid_by_key("ZAP-B1")
        iid = idx.get((zap, "R02"))
        if iid:
            http("PATCH", f"{base}/issues/{iid}", {"status": "fixed", "fixed_by": "one_click"})
            print(f"✓ issue #{iid} (R02 en zapata B-1) marcado corregido con 1 clic (sugerencia IA)")

        try:
            http("PATCH", f"{base}/snapshots/{s1['id']}/cde-state", {"cde_state": "SHARED"})
            print("  ! v1 pasó a SHARED — inesperado: tiene errores abiertos")
        except BackendError as ex:
            if ex.status == 409:
                print("✓ v1 → SHARED bloqueado (409) como manda el BEP §7: tiene errores abiertos")
            else:
                print(f"  ! v1 → SHARED devolvió {ex}")

        s2 = http("POST", f"{base}/snapshots", v2)
        print(f"✓ v2 enviada: snapshot #{s2['id']} ({s2['element_count']} elementos, "
              f"{s2['open_issue_count']} issues abiertos)")
        try:
            r = http("PATCH", f"{base}/snapshots/{s2['id']}/cde-state", {"cde_state": "SHARED"})
            print(f"✓ v2 → {r['cde_state']} aceptado: 0 errores abiertos")
        except BackendError as ex:
            print(f"✗ v2 → SHARED rechazado: {ex}")

        try:
            d = http("GET", f"{base}/budget/diff?from_snapshot_id={s1['id']}&to_snapshot_id={s2['id']}")
            print(f"✓ Presupuesto v1 S/ {d['total_from']:,.2f} → v2 S/ {d['total_to']:,.2f} "
                  f"(Δ S/ {d['delta_total']:,.2f}); elementos +{d['elements_added']} "
                  f"-{d['elements_removed']} ~{d['elements_modified']}")
        except (BackendError, KeyError, TypeError) as ex:
            print(f"  (no se pudo leer /budget/diff: {ex})")
    except BackendError as ex:
        print(f"\n✗ El backend rechazó la petición: {ex}")
        return 1
    except (urllib.error.URLError, OSError) as ex:
        print(f"\n✗ Se perdió la conexión con el backend: {ex}")
        return 2
    print("\nListo. Abre el dashboard para ver salud, issues, hilo por elemento y presupuesto 5D.")
    return 0


# ---------------------------------------------------------------------------
def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="Simulador del plugin Revit (Agente Profesor BIM)")
    ap.add_argument("--base", default="http://localhost:8000/api", help="URL base de la API")
    ap.add_argument("--dry-run", action="store_true", help="No usa red: escribe demo/out/*.json")
    args = ap.parse_args(argv)

    v1, v2, fb = build_snapshot("v1"), build_snapshot("v2"), build_feedback()
    print("Agente Profesor BIM — simulador del plugin")
    print(summarize(v1))
    print(summarize(v2))
    print(f"  feedback: {len(fb)} respuestas ({', '.join(sorted({f['reason'] for f in fb}))})")

    if args.dry_run:
        OUT.mkdir(parents=True, exist_ok=True)
        for name, obj in (("v1.json", v1), ("v2.json", v2), ("feedback.json", fb)):
            (OUT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n✓ Dry-run: payloads escritos en {OUT}")
        return 0
    return run_online(args.base, v1, v2, fb)


if __name__ == "__main__":
    sys.exit(main())
