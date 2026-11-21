# Backend — Agente Profesor BIM

API FastAPI que implementa `contracts/openapi.yaml` (todas las rutas bajo `/api`).
El backend **no** re-ejecuta reglas: guarda lo que envía el plugin y calcula estadísticas, presupuesto 5D y exportes.

## Ejecutar

Desde `backend/`:

```powershell
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

- Docs interactivas: http://localhost:8000/docs
- CORS habilitado para `http://localhost:5173` (dashboard).
- Al arrancar se valida `data/rules.json` contra `contracts/rules.schema.json`; si no cumple, el servidor no arranca.

Tests (desde la raíz del repo):

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests -q
```

## Variables de entorno

Se leen del entorno o de `.env` en la **raíz del repo** (ver `.env.example`).

| Variable | Uso | Defecto |
|---|---|---|
| `DATABASE_URL` | URL SQLAlchemy | `sqlite:///<repo>/backend/profesor_bim.db` |
| `LLM_PROVIDER`, `LLM_API_KEY`, `LLM_MODEL`, `LLM_BASE_URL` | Los usa el módulo `app/ai` (no el backend) | modo `mock` |

Los archivos de `data/` se resuelven relativos al código, no al directorio de trabajo.

## Estructura

```
app/
  main.py          FastAPI, CORS, handler 422 → {"detail": "..."}
  config.py db.py models.py schemas.py
  routers/         system, snapshots, issues, feedback, analysis, ai, exports
  services/        data (rules/uniclass/mapeo), snapshots (ingesta + ciclo de issues),
                   budget (5D + diff), stats (stats + facts), exports (BCF, 4D, COBie)
  ai/              módulo IA (lo mantiene el agente de IA)
```

## Comportamiento

- **POST /snapshots** es idempotente por `(project_code, version_label)`: el reenvío reemplaza elementos e issues
  del snapshot y conserva su `id` (se actualiza `created_at`).
- **Identidad de issue**: `(project_code, element_guid, rule_id, related_guid, issue_key)`. `issue_key` es `""`
  salvo en reglas `required_parameters` (R05), donde es el parámetro citado entre comillas en `message`
  (el plugin emite un issue por parámetro faltante), así cada parámetro se abre y se auto-corrige por separado.
  Si cambias el modelo con una BD ya creada, borra `backend/profesor_bim.db` (no hay migraciones).
  - viene y ya existía abierto → se actualiza `snapshot_id` (y severidad/mensaje);
  - viene y es nuevo → `open` con `first_seen_at`;
  - viene y estaba `fixed` → se reabre (regresión); si estaba `dismissed` sigue descartado;
  - estaba abierto y no viene → `fixed`, `resolved_at = ahora`, `fixed_by = manual` salvo que un PATCH ya lo hubiera fijado.
  - `discipline` del issue = disciplina del elemento en ese snapshot (`null` para reglas de documento, p. ej. R06).
- Cada snapshot guarda qué issues tenía y su estado *dentro de ese snapshot* (tabla `snapshot_issues`).
  Los conteos "abiertos en el snapshot X" (stats, gate CDE, `open_issue_count`, presupuesto, BCF) usan ese estado,
  así un snapshot viejo conserva su foto. Un PATCH actualiza el estado en el último snapshot del issue.
  `GET /issues?snapshot_id=X` lista los issues presentes en X con su estado dentro de X (contrato 0.2.0); `fixed_by` y `resolved_at` siguen siendo la historia global del issue.
- **PATCH /snapshots/{id}/cde-state**: `SHARED` y `PUBLISHED` → 409 si hay issues `error` abiertos en ese snapshot.
- **Conformidad**: elemento conforme = sin issues abiertos de severidad `error` ni `warning`. Elementos deduplicados por guid.
- **Presupuesto** (`services/budget.py`, BEP §8): cada guid una vez; motivos `sin_codigo`, `codigo_invalido`
  (no existe en la tabla o la categoría no está permitida), `sin_mapeo`, `sin_cantidad` (magnitud null/0; el elemento
  se cuenta una sola vez aunque fallen varias filas). Un elemento con una partida válida y otra sin cantidad
  (p. ej. placa con volumen pero sin área) aporta a la partida válida **y** se reporta como `sin_cantidad`.
  `cantidad` redondeada a 3 decimales, `subtotal = round(cantidad × precio, 2)`, `total = Σ subtotales`.
  `pendiente_validar` si el `estado` del mapeo contiene PENDIENTE. `is_official` solo en PUBLISHED.
  `overlap_warnings` = issues R04 abiertos en el snapshot.
- **Exportes**: BCF 2.1 (`bcf.version`, `project.bcfp`, una carpeta por issue abierto con `markup.bcf` y, si hay
  elemento, `viewpoint.bcfv` con `<Component IfcGuid=…><AuthoringToolId>UniqueId Revit</AuthoringToolId>`; el IfcGuid
  se deriva del UniqueId con el algoritmo de Revit). CSV 4D con la partida principal (primera fila del mapeo).
  COBie con hojas Contact, Facility, Floor, Type, Component.

## `facts` para `build_recommendations`

`GET /ai/recommendations` calcula este diccionario (`services/stats.py::compute_facts`) y lo pasa a
`app.ai.build_recommendations(facts)`. La IA solo puede citar estos valores. Antes de responder, el router quita del
`facts` de cada recomendación los valores `null` y convierte booleanos a 0/1 (el contrato admite number|string).

| Clave | Tipo | Significado |
|---|---|---|
| `snapshot_id` | int | Snapshot analizado (el más reciente si no se indica) |
| `project_code` | str | Proyecto |
| `version_label` | str | Versión |
| `cde_state` | str | WIP / SHARED / PUBLISHED / ARCHIVED |
| `is_official` | bool | true solo si PUBLISHED |
| `element_count` | int | Elementos únicos (por guid) |
| `conformance_pct` | float | % de elementos sin errores ni warnings abiertos (1 decimal) |
| `open_errors` | int | Issues `error` abiertos en el snapshot |
| `open_warnings` | int | Issues `warning` abiertos en el snapshot |
| `can_move_to_shared` | bool | `open_errors == 0` |
| `top_rule_id` | str \| null | Regla con más issues abiertos |
| `top_rule_name` | str \| null | Nombre de esa regla (rules.json) |
| `top_rule_open_count` | int | Issues abiertos de esa regla (0 si no hay) |
| `budget_total` | float | Total del presupuesto, PEN sin IGV |
| `unbudgeted_count` | int | Elementos no presupuestados |
| `unbudgeted_sin_codigo` | int | … por falta de código |
| `unbudgeted_codigo_invalido` | int | … por código inválido |
| `unbudgeted_sin_mapeo` | int | … por código sin partida |
| `unbudgeted_sin_cantidad` | int | … por magnitud null/0 |
| `overlap_warnings` | int | Issues R04 abiertos |
| `previous_snapshot_id` | int \| null | Snapshot anterior del mismo proyecto |
| `previous_version_label` | str \| null | Su versión |
| `delta_total` | float \| null | Total actual − total anterior |
| `delta_pct` | float \| null | `delta_total / total_anterior × 100` (2 decimales; null si no hay anterior o era 0) |
| `feedback_top_reason` | str \| null | Motivo de feedback más frecuente |
| `feedback_top_count` | int | Cuántas veces (0 si no hay feedback) |
| `fixed_one_click` | int | Issues corregidos en 1 clic (proyecto) |
| `fixed_manual` | int | Issues corregidos a mano (proyecto) |

## Contrato con `app.ai`

```python
from app.ai import explain_rule, suggest_classification, build_recommendations, llm_mode
explain_rule(rule: dict, element: dict | None) -> dict            # {rule_id, text, cached, mode}
suggest_classification(element: dict, candidates: list[dict]) -> dict  # {element_guid, candidates, suggested_code, reason, mode}
build_recommendations(facts: dict) -> list[dict]                   # list[Recommendation]
llm_mode() -> str
```

El router busca la regla en `rules.json` (404 si no existe), filtra los candidatos Uniclass por la categoría del
elemento y fuerza `suggested_code = null` si la IA devuelve un código fuera de `candidates`.
