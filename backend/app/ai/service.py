"""Funciones de IA usadas por el router del backend."""
from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import unicodedata
from pathlib import Path

from . import llm
from .guard import check_text

CACHE_DIR = Path(os.getenv("LLM_CACHE_DIR") or Path(__file__).resolve().parent / ".cache")
_CACHE_FILE = "explanations.json"
_mem_cache: dict[str, str] = {}
_lock = threading.Lock()


# --------------------------------------------------------------------------- caché
def _cache_path() -> Path:
    return Path(CACHE_DIR) / _CACHE_FILE


def _load_disk() -> dict:
    try:
        return json.loads(_cache_path().read_text(encoding="utf-8"))
    except Exception:
        return {}


def _cache_get(key: str) -> str | None:
    with _lock:
        if key in _mem_cache:
            return _mem_cache[key]
        val = _load_disk().get(key)
        if isinstance(val, str):
            _mem_cache[key] = val
            return val
    return None


def _cache_put(key: str, text: str) -> None:
    with _lock:
        _mem_cache[key] = text
        try:
            path = _cache_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            data = _load_disk()
            data[key] = text
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
            os.replace(tmp, path)
        except Exception:
            pass  # la caché en disco es opcional


def clear_memory_cache() -> None:
    with _lock:
        _mem_cache.clear()


def _rule_hash(rule: dict) -> str:
    raw = json.dumps(rule, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


# --------------------------------------------------------------------------- explain_rule
def _fix_label(rule: dict) -> str:
    return ((rule.get("fix") or {}).get("label") or "revisar el elemento").strip()


def _mock_explanation(rule: dict) -> str:
    expl = (rule.get("explanation") or rule.get("name") or "").strip()
    return f"{expl} Cómo corregirlo: {_fix_label(rule)}."


def _element_example(element: dict | None) -> str:
    if not element:
        return ""
    type_name = element.get("type_name") or "sin nombre"
    bits = [b for b in (element.get("category"), element.get("level")) if b]
    ctx = f" ({', '.join(bits)})" if bits else ""
    return f"\n\nEjemplo en tu modelo: el tipo «{type_name}»{ctx} está afectado por esta regla."


def explain_rule(rule: dict, element: dict | None = None) -> dict:
    rule_id = str(rule.get("id") or "")
    mode = llm.llm_mode()
    key = f"{mode}:{rule_id}:{_rule_hash(rule)}"
    cached = True
    text = _cache_get(key)
    if text is None:
        cached = False
        if mode != "mock":
            bep = rule.get("bep_ref") or "del BEP"
            messages = [
                {
                    "role": "system",
                    "content": (
                        "Eres un profesor BIM que explica reglas del BEP a modeladores Revit. "
                        "Responde en español, tono didáctico, en 3 a 5 oraciones, texto plano sin listas ni markdown. "
                        "No contradigas la explicación oficial de la regla ni inventes cifras."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Regla {rule_id}: {rule.get('name', '')}\n"
                        f"Severidad: {rule.get('severity', '')}\n"
                        f"Explicación oficial: {rule.get('explanation', '')}\n"
                        f"Sección del BEP: {bep}\n"
                        f"Corrección propuesta: {_fix_label(rule)}\n\n"
                        f"Explica por qué importa esta regla y cómo corregirla. Menciona la sección {bep} del BEP."
                    ),
                },
            ]
            text = llm.chat(messages, max_tokens=400)
            if text is None:
                mode = "mock"
        if text is None:
            text = _mock_explanation(rule)
            key = f"mock:{rule_id}:{_rule_hash(rule)}"
        _cache_put(key, text)
    return {"rule_id": rule_id, "text": text + _element_example(element), "cached": cached, "mode": mode}


# --------------------------------------------------------------------------- suggest_classification
def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


# token del elemento -> (fragmento del title_es normalizado, peso)
_KEYWORDS: dict[str, tuple[str, int]] = {
    "ca": ("concreto", 1),
    "concreto": ("concreto", 1),
    "hormigon": ("concreto", 1),
    "lad": ("albanil", 2),
    "ladrillo": ("albanil", 2),
    "albanil": ("albanil", 2),
    "albanileria": ("albanil", 2),
    "drywall": ("drywall", 2),
    "dw": ("drywall", 2),
    "tabique": ("drywall", 2),
    "alig": ("aligerada", 2),
    "aligerada": ("aligerada", 2),
    "mac": ("maciza", 2),
    "maciza": ("maciza", 2),
    "acero": ("acero", 2),
    "ac": ("acero", 2),
    "metalica": ("acero", 2),
    "zap": ("zapata", 2),
    "zapata": ("zapata", 2),
    "corrido": ("corrido", 2),
    "cim": ("corrido", 1),
}


def _element_tokens(element: dict) -> set[str]:
    parts = [element.get("type_name") or "", element.get("family_name") or ""]
    params = element.get("parameters") or {}
    if isinstance(params, dict):
        parts += [str(v) for v in params.values() if v]
    return {t for t in re.split(r"[^a-z0-9]+", _norm(" ".join(parts))) if t}


def _mock_suggest(element: dict, candidates: list[dict]) -> tuple[str | None, str | None]:
    if len(candidates) == 1:
        c = candidates[0]
        return c["code"], f"Único código válido para la categoría: {c.get('title_es', '')}."
    tokens = _element_tokens(element)
    scores: dict[str, int] = {}
    hits: dict[str, list[str]] = {}
    for c in candidates:
        title = _norm(c.get("title_es") or "")
        for tok in tokens:
            kw = _KEYWORDS.get(tok)
            if kw and kw[0] in title:
                scores[c["code"]] = scores.get(c["code"], 0) + kw[1]
                hits.setdefault(c["code"], []).append(tok.upper())
    if not scores:
        return None, None
    best = max(scores.values())
    winners = [code for code, s in scores.items() if s == best]
    if len(winners) != 1:
        return None, None
    code = winners[0]
    title = next(c.get("title_es", "") for c in candidates if c["code"] == code)
    return code, f"Coincidencia por palabra clave ({', '.join(sorted(set(hits[code])))}) con «{title}»."


def _parse_json_obj(text: str) -> dict | None:
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
    except Exception:
        return None
    return obj if isinstance(obj, dict) else None


def suggest_classification(element: dict, candidates: list[dict]) -> dict:
    element = element or {}
    candidates = list(candidates or [])
    codes = {c.get("code") for c in candidates}
    mode = llm.llm_mode()
    code: str | None = None
    reason: str | None = None
    answer = None
    if mode != "mock" and candidates:
        listing = "\n".join(f"- {c.get('code')}: {c.get('title_es', '')}" for c in candidates)
        elem = {k: element.get(k) for k in ("category", "family_name", "type_name", "parameters")}
        messages = [
            {
                "role": "system",
                "content": (
                    "Clasificas elementos Revit con Uniclass 2015 (tabla Ss). Elige SOLO uno de los códigos "
                    "listados. Responde únicamente JSON: {\"code\": \"<código o null>\", \"reason\": \"<1 oración en español>\"}."
                ),
            },
            {
                "role": "user",
                "content": f"Elemento: {json.dumps(elem, ensure_ascii=False)}\nCódigos permitidos:\n{listing}",
            },
        ]
        answer = llm.chat(messages, max_tokens=200, temperature=0)
        if answer is None:
            mode = "mock"
        else:
            obj = _parse_json_obj(answer)
            if obj is None:
                reason = "Respuesta del LLM no válida; asigna el código manualmente."
            else:
                cand = obj.get("code")
                if isinstance(cand, str) and cand.strip() in codes:
                    code = cand.strip()
                    r = obj.get("reason")
                    reason = r.strip() if isinstance(r, str) and r.strip() else None
                else:
                    reason = "El LLM no propuso un código de la lista; asigna el código manualmente."
    if mode == "mock":
        code, reason = _mock_suggest(element, candidates)
    if code is not None and code not in codes:  # garantía final del contrato
        code = None
    return {
        "element_guid": element.get("guid"),
        "candidates": candidates,
        "suggested_code": code,
        "reason": reason,
        "mode": mode,
    }


# --------------------------------------------------------------------------- build_recommendations
def _fmt_int(v) -> str:
    return f"{int(round(float(v))):,}"


def _fmt_money(v) -> str:
    return f"S/ {abs(float(v)):,.2f}"


def _fmt_pct(v) -> str:
    return f"{abs(float(v)):.1f}%"


def _num(v) -> float | None:
    if isinstance(v, bool) or v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _pick(facts: dict, *keys) -> dict:
    out = {}
    for k in keys:
        v = facts.get(k)
        if v is None or isinstance(v, bool):
            continue
        if isinstance(v, (int, float, str)):
            out[k] = v
    return out


_PRIO_ORDER = {"alta": 0, "media": 1, "baja": 2}


def _deterministic(facts: dict) -> list[dict]:
    f = facts or {}
    recs: list[dict] = []

    def add(rid, title, prio, rfacts, text):
        recs.append({"id": rid, "title": title, "priority": prio, "facts": rfacts, "text": text})

    errors = _num(f.get("open_errors"))
    if errors and errors > 0:
        rf = _pick(f, "open_errors", "top_rule_id", "top_rule_name", "top_rule_open_count")
        t = f"Hay {_fmt_int(errors)} errores abiertos en el modelo."
        if "top_rule_id" in rf and _num(f.get("top_rule_open_count")) is not None:
            name = f" ({rf['top_rule_name']})" if "top_rule_name" in rf else ""
            t += (f" La regla con más incidencias es {rf['top_rule_id']}{name}, con "
                  f"{_fmt_int(f['top_rule_open_count'])} abiertas: corrígela primero.")
        add("rec_errores", "Corregir los errores abiertos", "alta", rf, t)

    unb = _num(f.get("unbudgeted_count"))
    if unb and unb > 0:
        rf = _pick(f, "unbudgeted_count", "unbudgeted_sin_codigo")
        t = f"{_fmt_int(unb)} elementos quedaron fuera del presupuesto 5D"
        sc = _num(f.get("unbudgeted_sin_codigo"))
        t += f", de ellos {_fmt_int(sc)} sin código Uniclass." if sc else "."
        t += " Asigna su clasificación para que el costo no se subestime."
        add("rec_no_presupuestados", "Completar la clasificación para el 5D", "alta", rf, t)

    ov = _num(f.get("overlap_warnings"))
    if ov and ov > 0:
        rf = _pick(f, "overlap_warnings")
        add("rec_superposiciones", "Unir geometría muro–viga", "media", rf,
            f"Se detectaron {_fmt_int(ov)} superposiciones muro–viga (R04) que duplican volumen de concreto "
            "en el metrado. Une la geometría antes de compartir.")

    dt, dp = _num(f.get("delta_total")), _num(f.get("delta_pct"))
    if (dt is not None and dt != 0) or (dp is not None and dp != 0):
        rf = _pick(f, "delta_total", "delta_pct")
        sentido = "subió" if (dt if dt is not None else dp) > 0 else "bajó"
        partes = []
        if dt is not None and dt != 0:
            partes.append(_fmt_money(dt))
        if dp is not None and dp != 0:
            partes.append(_fmt_pct(dp) if not partes else f"({_fmt_pct(dp)})")
        prio = "media" if dp is not None and abs(dp) >= 5 else "baja"
        add("rec_delta", "Revisar la variación del presupuesto", prio, rf,
            f"El presupuesto {sentido} {' '.join(partes)} respecto a la versión anterior. "
            "Verifica que el cambio corresponda a modificaciones de diseño reales.")

    reason = f.get("feedback_top_reason")
    if isinstance(reason, str) and reason.strip():
        rf = _pick(f, "feedback_top_reason", "feedback_top_count")
        cnt = _num(f.get("feedback_top_count"))
        extra = f" ({_fmt_int(cnt)} veces)" if cnt else ""
        add("rec_feedback", "Atender el feedback del equipo", "baja", rf,
            f"El motivo más reportado por los modeladores es «{reason.strip()}»{extra}. "
            "Revisa si la regla necesita ajuste o una capacitación breve.")

    state, can = f.get("cde_state"), f.get("can_move_to_shared")
    if state == "WIP" and can is True:
        rf = _pick(f, "cde_state", "conformance_pct")
        t = "El modelo no tiene errores abiertos y puede pasar de WIP a SHARED."
        if "conformance_pct" in rf:
            t += f" Conformidad actual: {_fmt_pct(rf['conformance_pct'])}."
        add("rec_cde", "Mover el modelo a SHARED", "media", rf, t)
    elif state == "WIP" and can is False:
        rf = _pick(f, "cde_state", "open_errors")
        t = "El modelo sigue en WIP y aún no puede pasar a SHARED"
        t += f": primero hay que cerrar {_fmt_int(errors)} errores." if errors else "."
        add("rec_cde", "Desbloquear el paso a SHARED", "alta" if errors else "media", rf, t)

    conf = _num(f.get("conformance_pct"))
    if conf is not None and not any(r["id"] == "rec_cde" and "conformance_pct" in r["facts"] for r in recs):
        rf = _pick(f, "conformance_pct")
        prio = "alta" if conf < 70 else ("media" if conf < 90 else "baja")
        add("rec_conformidad", "Seguir la conformidad con el BEP", prio, rf,
            f"La conformidad del modelo con el BEP es {_fmt_pct(conf)}. "
            + ("Mantén el control en cada envío." if conf >= 90 else "Prioriza las reglas de severidad error."))

    bt = _num(f.get("budget_total"))
    if bt is not None and len(recs) < 3:
        add("rec_presupuesto", "Validar el presupuesto estimado", "baja", _pick(f, "budget_total", "cde_state"),
            f"El presupuesto estimado del modelo es {_fmt_money(bt)}. Solo es oficial cuando la versión está en PUBLISHED.")

    fillers = [
        ("rec_validar", "Validar tras cada cambio",
         "Vuelve a ejecutar la validación después de cada corrección para mantener el modelo alineado con el BEP."),
        ("rec_bep", "Repasar el BEP con el equipo",
         "Repasa con el equipo las reglas de nombres y clasificación del BEP antes del próximo envío."),
        ("rec_datos", "Enviar un snapshot actualizado",
         "Envía un snapshot del modelo desde el plugin para obtener indicadores de conformidad y presupuesto."),
    ]
    for rid, title, text in fillers:
        if len(recs) >= 3:
            break
        add(rid, title, "baja", {}, text)

    recs.sort(key=lambda r: _PRIO_ORDER[r["priority"]])
    return recs[:5]


def _rewrite(rec: dict) -> str | None:
    messages = [
        {
            "role": "system",
            "content": (
                "Reescribes recomendaciones para un jefe de proyecto (PM) de construcción, en español claro, "
                "en 1 a 3 oraciones, texto plano. Usa ÚNICAMENTE los números presentes en FACTS (puedes "
                "formatearlos, p. ej. S/ 1,234.50 o 45.2%). No agregues ningún otro número, fecha, porcentaje, "
                "sección ni cantidad. Devuelve solo el texto."
            ),
        },
        {
            "role": "user",
            "content": (
                f"TÍTULO: {rec['title']}\nFACTS: {json.dumps(rec['facts'], ensure_ascii=False)}\n"
                f"TEXTO BASE: {rec['text']}"
            ),
        },
    ]
    return llm.chat(messages, max_tokens=250)


def build_recommendations(facts: dict) -> list[dict]:
    recs = _deterministic(facts or {})
    llm_ok = llm.llm_mode() != "mock"
    out = []
    for rec in recs:
        text, mode = rec["text"], "mock"
        if llm_ok:
            new = _rewrite(rec)
            if new is None:
                llm_ok = False  # fallo de red/HTTP: no seguir esperando timeouts
            else:
                ok, _bad = check_text(new, rec["facts"])
                if ok:
                    text, mode = new, llm.llm_mode()
        out.append({**rec, "text": text, "mode": mode})
    return out
