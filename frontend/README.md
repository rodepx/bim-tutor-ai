# Dashboard — Agente Profesor BIM

Panel web (React + Vite + TypeScript) para el PM y el jurado: salud del modelo, issues, recomendaciones IA,
presupuesto 5D y exportes. Consume la API definida en `../contracts/openapi.yaml` (base `/api`).

## Requisitos

- Node.js 20 o superior (probado con Node 26 / npm 11).
- Backend en `http://localhost:8000` (opcional: sin backend se usan datos de demostración).

## Instalación y uso

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173  (proxy /api → http://localhost:8000)
```

Otros scripts:

| Script | Qué hace |
|---|---|
| `npm run build` | Verifica tipos (`tsc`) y genera `dist/` |
| `npm run preview` | Sirve `dist/` para revisar el build |
| `npm test` | Pruebas (vitest): formato es-PE, cliente y fallback al mock |
| `npm run gen:api` | Regenera `src/api/schema.d.ts` desde `../contracts/openapi.yaml` |

## Modo demostración (mock)

El panel usa datos de ejemplo tipados (`src/api/mock.ts`) cuando:

1. `VITE_USE_MOCK=true` (por ejemplo `VITE_USE_MOCK=true npm run dev`, o en `.env.local`), o
2. `GET /api/health` falla o no responde en 2,5 s.

En ese caso aparece la etiqueta morada **«Datos de demostración»** en la barra superior y los botones de
exporte se deshabilitan (los archivos los genera el backend). El escenario de ejemplo tiene dos versiones:
`v1` en WIP con 10 errores (no puede pasar a SHARED: el botón «Mover estado» muestra el 409) y `v2` en SHARED,
con issues de las 7 reglas, microencuestas, presupuesto con las partidas de `data/mapeo_partidas.csv` y su diferencia.

## Tipos de la API

`src/api/schema.d.ts` se genera con `openapi-typescript`; no editarlo a mano. Si cambia el contrato:

```bash
npm run gen:api && npm run build
```

`src/api/types.ts` expone alias legibles (`Stats`, `Budget`, `Issue`…) y la interfaz `ApiClient`, que implementan
tanto `src/api/client.ts` (HTTP) como `src/api/mock.ts`.

## Estructura

```
src/
  api/        schema.d.ts (generado), types.ts, client.ts, mock.ts
  pages/      SaludPage, IssuesPage, RecomendacionesPage, PresupuestoPage, ExportesPage
  components/ ui.tsx (tarjetas, barras, badges)
  format.ts   formato es-PE (S/, porcentajes, fechas en hora de Lima)
  rules.ts    etiquetas en español (reglas, motivos de feedback, estados CDE)
```

Navegación por hash (`#/salud`, `#/issues`, `#/recomendaciones`, `#/presupuesto`, `#/exportes`).
El selector «Versión» de la barra superior aplica a todas las secciones (por defecto, la más reciente).
