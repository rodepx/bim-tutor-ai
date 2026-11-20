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

## Cómo correrlo

Requisitos: entorno Python en `backend\.venv` (ver `backend/README.md`) y Node.js 20+.
Desde la raíz del repo:

```powershell
powershell -ExecutionPolicy Bypass -File .\run_demo.ps1
```

Abre dos ventanas (backend en `:8000`, dashboard en `:5173`), espera a `/api/health`, carga las versiones v1/v2
con `demo/seed.py` e imprime la URL del dashboard: http://localhost:5173. Opciones: `-FreshDb` (borra la BD local
antes de arrancar) y `-NoSeed` (no carga datos). Para detener, cierra las dos ventanas.

> Todo dato en `data/*.csv` marcado `PENDIENTE VALIDAR POR CONSTRUCCIÓN` es de ejemplo.
