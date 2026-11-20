# Módulo IA (`backend/app/ai`)

Funciones que importa el router: `explain_rule`, `suggest_classification`, `build_recommendations`, `llm_mode`.

## Modos
- **openrouter**: chat completions compatible con OpenAI vía `httpx` (timeout 20 s).
- **mock**: determinista, sin red. Se usa si `LLM_PROVIDER=mock`, si falta `LLM_API_KEY`,
  o ante cualquier error de red/HTTP/respuesta (nunca lanza excepción). Cada respuesta
  informa en `mode` el modo del texto realmente usado.

## Variables de entorno
Se lee `.env` de la raíz del repo si existe (sin pisar variables ya definidas).

| Variable | Por defecto |
|---|---|
| `LLM_PROVIDER` | `openrouter` (`openrouter` \| `mock`) |
| `LLM_API_KEY` | — (sin clave → mock) |
| `LLM_MODEL` | `anthropic/claude-sonnet-5.5` |
| `LLM_BASE_URL` | `https://openrouter.ai/api/v1` |
| `LLM_CACHE_DIR` | `backend/app/ai/.cache` |

## Caché de explicaciones
Clave `modo:rule_id:hash(regla)`: si la regla cambia en `rules.json`, se regenera.
En memoria y en `.cache/explanations.json` (ignorado por git). La frase de ejemplo con
el elemento se agrega fuera de la caché y sin llamar al LLM.

## Clasificación
El LLM debe responder JSON `{"code", "reason"}`. Si el código no está exactamente en
`candidates` o el JSON es inválido → `suggested_code = null`. Mock: coincidencia de
palabras clave (CA/concreto, LAD/ladrillo, drywall, ALIG, MAC, acero…) con `title_es`;
si hay un único candidato se devuelve ese.

## Guardia anti-alucinación (recomendaciones)
Las recomendaciones se arman de forma determinista desde `facts`; el LLM solo reescribe
cada texto recibiendo únicamente los facts de esa recomendación. Luego se extraen todos los
números del texto (`1,234.50`, `1 234,5`, `S/ 12,345`, `45%`, `45.2 %`) y cada uno debe
coincidir (redondeado a 0–2 decimales, en valor absoluto) con un valor de esos facts.
Los identificadores pegados a letras (`R04`, `FC210`, `5D`) se ignoran. Si un número no
coincide, se descarta el texto del LLM y se usa la plantilla (`mode: "mock"`).

## Tests
`backend\.venv\Scripts\python.exe -m pytest backend/tests_ai -q` (sin red; HTTP simulado).
