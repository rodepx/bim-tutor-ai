"""Guardia anti-alucinación: todo número del texto debe venir de los facts."""
from __future__ import annotations

import re
from decimal import ROUND_HALF_UP, Decimal
from typing import Iterable

# Número con separadores de miles (coma, punto, espacio, nbsp) y decimales opcionales.
# No debe ir pegado a letras/dígitos: así se ignoran identificadores como R04, FC210,
# e25, m3 o 5D (los ids de regla quedan permitidos por construcción).
_NUM_RE = re.compile(
    r"(?<![A-Za-z0-9_])"
    r"(\d{1,3}(?:[,.   ]\d{3})+(?:[.,]\d+)?|\d+(?:[.,]\d+)?)"
    r"(?![A-Za-z0-9_])"
)
# Unidades pegadas al número ("120m2", "35kg") se separan para no ocultar el número.
_UNIT_RE = re.compile(r"(\d)(m2|m3|m²|m³|kg|ml|und)(?![A-Za-z0-9])", re.I)


def _interpretations(token: str) -> set[float]:
    """Valores posibles de un token numérico (formato es-PE / en-US / europeo)."""
    t = token.replace(" ", " ").replace(" ", " ").replace(" ", "")  # espacio = miles
    out: set[float] = set()
    has_c, has_d = "," in t, "." in t
    try:
        if has_c and has_d:
            dec = "," if t.rfind(",") > t.rfind(".") else "."
            thou = "." if dec == "," else ","
            out.add(float(t.replace(thou, "").replace(dec, ".")))
        elif has_c or has_d:
            sep = "," if has_c else "."
            parts = t.split(sep)
            if len(parts) > 2:  # 1,234,567
                out.add(float(t.replace(sep, "")))
            else:
                out.add(float(parts[0] + "." + parts[1]))  # decimal
                if len(parts[1]) == 3:  # ambiguo: también miles
                    out.add(float(parts[0] + parts[1]))
        else:
            out.add(float(t))
    except ValueError:
        pass
    return out


def extract_numbers(text: str) -> list[tuple[str, set[float]]]:
    text = _UNIT_RE.sub(lambda m: f"{m.group(1)} {m.group(2)}", text or "")
    return [(m.group(1), _interpretations(m.group(1))) for m in _NUM_RE.finditer(text)]


def allowed_values(facts: dict) -> set[float]:
    vals: set[float] = set()
    for v in (facts or {}).values():
        if isinstance(v, bool) or v is None:
            continue
        if isinstance(v, (int, float)):
            vals.add(abs(float(v)))
        elif isinstance(v, str):  # números contenidos en hechos de texto
            for _, interp in extract_numbers(v):
                vals.update(interp)
    return vals


def _round_half_up(a: float, nd: int) -> float:
    q = Decimal(1).scaleb(-nd)
    return float(Decimal(repr(a)).quantize(q, rounding=ROUND_HALF_UP))


def _matches(value: float, allowed: Iterable[float]) -> bool:
    for a in allowed:
        refs = [a] + [round(a, nd) for nd in (0, 1, 2)] + [_round_half_up(a, nd) for nd in (0, 1, 2)]
        for ref in refs:
            if abs(value - ref) < 1e-9:
                return True
    return False


def check_text(text: str, facts: dict) -> tuple[bool, list[str]]:
    """(ok, números_no_permitidos). Se compara en valor absoluto."""
    allowed = allowed_values(facts)
    bad = [tok for tok, interp in extract_numbers(text) if not any(_matches(v, allowed) for v in interp)]
    return (not bad, bad)
