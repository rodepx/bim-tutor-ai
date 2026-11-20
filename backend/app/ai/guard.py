"""Guardia anti-alucinación: todo número del texto debe venir de los facts."""
from __future__ import annotations

import re
from decimal import ROUND_HALF_UP, Decimal
from typing import Iterable
import unicodedata

# Número con separadores de miles (coma, punto, espacio, nbsp) y decimales opcionales.
# No debe ir precedido de letra/dígito/_: así se ignoran identificadores como R04, FC210,
# e25, m3 o Ss_20_10_10 (los ids de regla quedan permitidos por construcción).
# Si va seguido de letras SÍ cuenta ("58elementos", "12xyz"), salvo una sola mayúscula
# (5D, 4D, 3D: nombres de dimensión BIM, ver _IDENT_SUFFIX_RE).
_NUM_RE = re.compile(
    r"(?<!\w)"
    r"(\d{1,3}(?:[,.   ]\d{3})+(?:[.,]\d+)?|\d+(?:[.,]\d+)?)"
    r"(?![0-9_])"
)
_IDENT_SUFFIX_RE = re.compile(r"[A-Z](?![^\W\d_])")
# Unidades pegadas al número ("120m2", "35kg") se separan para no ocultar el número.
_UNIT_RE = re.compile(r"(\d)(m2|m3|m²|m³|kg|ml|und)(?![A-Za-z0-9])", re.I)


def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)).lower()


# Números escritos con palabras (es). Se excluyen "un/uno/una" (artículos) y ordinales.
_UNITS = ["cero", "", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve", "diez",
          "once", "doce", "trece", "catorce", "quince", "dieciseis", "diecisiete", "dieciocho", "diecinueve", "veinte"]
_WORD_VALUES: dict[str, float] = {w: float(i) for i, w in enumerate(_UNITS) if w}
_WORD_VALUES.update({"veinti" + w: 20.0 + i for i, w in enumerate(_UNITS[:10]) if w and i > 1})
_WORD_VALUES.update({"veintiuno": 21.0, "veintiun": 21.0, "veintiuna": 21.0})
for _i, _w in enumerate(["treinta", "cuarenta", "cincuenta", "sesenta", "setenta", "ochenta", "noventa"], start=3):
    _WORD_VALUES[_w] = _i * 10.0
for _i, _w in enumerate(["doscientos", "trescientos", "cuatrocientos", "quinientos", "seiscientos",
                         "setecientos", "ochocientos", "novecientos"], start=2):
    _WORD_VALUES[_w] = _i * 100.0
    _WORD_VALUES[_w[:-2] + "as"] = _i * 100.0  # doscientas…
_WORD_VALUES.update({"cien": 100.0, "ciento": 100.0, "mil": 1000.0, "millon": 1e6, "millones": 1e6,
                     "docena": 12.0, "docenas": 12.0, "decena": 10.0, "decenas": 10.0, "centenar": 100.0,
                     "centenares": 100.0, "miles": 1000.0})
_WORD_RE = re.compile(r"[^\W\d_]+")


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
    """Números en cifras (y, si ``words``, también escritos con palabras: "diez", "mil")."""
    return _extract(text, words=True)


def _extract(text: str, words: bool) -> list[tuple[str, set[float]]]:
    text = _UNIT_RE.sub(lambda m: f"{m.group(1)} {m.group(2)}", text or "")
    found: list[tuple[int, str, set[float]]] = []
    for m in _NUM_RE.finditer(text):
        if _IDENT_SUFFIX_RE.match(text, m.end()):
            continue  # 5D, 4D, 3D
        found.append((m.start(), m.group(1), _interpretations(m.group(1))))
    if words:
        # "por ciento" no es la cifra 100: el número que lo precede ya se valida.
        for m in _WORD_RE.finditer(re.sub(r"(?i)\bpor\s+ciento\b", lambda x: " " * len(x.group(0)), text)):
            v = _WORD_VALUES.get(_strip_accents(m.group(0)))
            if v is not None:
                found.append((m.start(), m.group(0), {v}))
    found.sort(key=lambda t: t[0])
    return [(tok, vals) for _, tok, vals in found]


def allowed_values(facts: dict) -> set[float]:
    vals: set[float] = set()
    for v in (facts or {}).values():
        if isinstance(v, bool) or v is None:
            continue
        if isinstance(v, (int, float)):
            vals.add(abs(float(v)))
        elif isinstance(v, str):  # números en cifras contenidos en hechos de texto
            for _, interp in _extract(v, words=False):
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
