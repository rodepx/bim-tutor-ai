# Agente Profesor BIM

Hackathon BIM + IA, Reto 3: gestión de costos y presupuestos.

Hace cumplir el BEP (NTP-ISO 19650 + Uniclass) mientras se modela en Revit y, con esos datos limpios,
genera el presupuesto 5D automáticamente.

| Carpeta | Contenido | Dueño |
|---|---|---|
| `docs/` | BEP mínimo | Datos |
| `contracts/` | `rules.schema.json`, `openapi.yaml`. **No se cambian sin avisar.** | Todos (solo lectura) |
| `data/` | `rules.json`, `uniclass_subset.csv`, `mapeo_partidas.csv` | Datos |
| `plugin/` | Plugin Revit 2027 (C#, .NET 10) | Plugin |
| `backend/` | FastAPI + SQLite, presupuesto 5D, exportes, módulo IA en `backend/app/ai/` | Backend / IA |
| `frontend/` | Dashboard React + Vite + TypeScript | Frontend |
| `demo/` | `seed.py` y guion de la demo | Datos/Demo |

Flujo: el plugin valida en Revit con `data/rules.json` → envía snapshot de elementos + issues al backend →
el backend calcula stats y presupuesto → el dashboard los muestra → la IA explica y recomienda solo con números del backend.

> Todo dato en `data/*.csv` marcado `PENDIENTE VALIDAR POR CONSTRUCCIÓN` es de ejemplo.
