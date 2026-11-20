# Plugin Revit — Agente Profesor BIM

Add-in para **Revit 2027 (.NET 10)** que hace cumplir el BEP (`docs/BEP.md`) mientras se modela:
valida con `data/rules.json` + `data/uniclass_subset.csv`, muestra los issues en un panel acoplable,
corrige en 1 clic y envía snapshots al backend (`contracts/openapi.yaml`).

## Estructura

| Proyecto | Qué contiene |
|---|---|
| `ProfesorBim.Core` (net10.0) | Núcleo **sin tipos de Revit**: modelos de reglas, `RuleEngine` (todos los `check`), tabla Uniclass, DTOs snake_case y `BackendClient` (HttpClient único, async, timeouts). |
| `ProfesorBim.Revit` (net10.0-windows, WPF) | Add-in: ribbon, `DockablePane`, lectura de elementos (`FilteredElementCollector`), detección de superposición, validación en vivo, fixes vía `ExternalEvent`. Genera `ProfesorBim.dll`. |
| `ProfesorBim.Tests` (xUnit) | Pruebas del motor contra los `data/*.json/csv` reales + contrato JSON. |

Flujo interno:

- **Lectura** (hilo de Revit): categorías de `rules.json` → `ElementData` (UniqueId, ElementId, `OST_*`, disciplina, familia, tipo,
  código Uniclass —`Uniclass_Codigo` y luego los `fallback_parameter_names`, primero en el tipo y luego en la instancia—, nivel,
  `volume_m3`/`area_m2`/`length_m` convertidos con `UnitUtils` + `UnitTypeId`; puertas/ventanas `area_m2 = ancho × alto`; parámetros LOIN en `parameters`).
- **no_overlap**: `ElementIntersectsElementFilter` (con prefiltro `BoundingBoxIntersectsFilter`) entre `category_a` y `category_b`;
  los pares ya unidos (`JoinGeometryUtils.AreElementsJoined`) se ignoran si `ignore_if_joined`.
- **Validación en vivo**: `DocumentChanged` solo acumula ids; en `Idling`, tras `live_validation_debounce_ms` sin cambios, se revalidan en lote
  únicamente los elementos cambiados (y las instancias de un tipo modificado). Los borrados limpian sus issues.
- **Cambios al modelo**: siempre por `ExternalEvent` + `Transaction` (`RevitTaskQueue`, `FixService`).
- **HTTP**: nunca en el hilo de la API; si el backend no responde se muestra un mensaje de estado y la validación local sigue.

## Compilar

Requisitos: .NET SDK 10 y Revit 2027 instalado en `C:\Program Files\Autodesk\Revit 2027\`
(otra ruta: `dotnet build -p:RevitInstallDir="D:\Revit 2027\"`).

```powershell
dotnet build plugin/ProfesorBim.sln
dotnet test  plugin/ProfesorBim.sln
```

Salida: `plugin/ProfesorBim.Revit/bin/Debug/` → `ProfesorBim.dll`, `ProfesorBim.Core.dll`, `profesorbim.settings.json`,
`data/rules.json`, `data/uniclass_subset.csv`, `ProfesorBim.addin`.

## Instalar

1. Cierra Revit.
2. Copia la salida del build a una carpeta `ProfesorBim` dentro de la carpeta de add-ins y el `.addin` al lado:

```powershell
$addins = "$env:AppData\Autodesk\Revit\Addins\2027"
$out    = "plugin\ProfesorBim.Revit\bin\Debug"
New-Item -ItemType Directory -Force "$addins\ProfesorBim" | Out-Null
Copy-Item "$out\*" "$addins\ProfesorBim" -Recurse -Force -Exclude ProfesorBim.addin
Copy-Item "$out\ProfesorBim.addin" $addins -Force
```

   Resultado: `%AppData%\Autodesk\Revit\Addins\2027\ProfesorBim.addin` (apunta a `ProfesorBim\ProfesorBim.dll`).
3. Abre Revit 2027. La primera vez Revit pregunta por el add-in sin firma: elige **Cargar siempre**.
4. Aparece la pestaña **Profesor BIM** con los botones **Panel**, **Validar todo** y **Enviar al backend**.

AddInId fijo: `4D6CDDB7-4D7C-4FB4-BBBA-2FD9EC8B8741` · DockablePaneId: `FA6E7758-503D-43D2-A987-28BFA7E15439`.

## Configurar

`profesorbim.settings.json` junto a la DLL (sin secretos):

```json
{
  "base_url": "http://localhost:8000/api",
  "timeout_seconds": 10,
  "live_validation": true,
  "live_validation_debounce_ms": 600,
  "rules_path": "data/rules.json",
  "uniclass_path": null
}
```

- `rules_path` / `uniclass_path`: relativas a la carpeta de la DLL o absolutas (p. ej. apuntar a `C:\...\repo\data\rules.json`
  para editar reglas sin recompilar). Si `uniclass_path` es `null` se usa `classification.table_file` de `rules.json`.
- Las llamadas de IA y el envío de snapshots usan 3× `timeout_seconds`.
- Los cambios se leen al iniciar Revit.

## Uso

- **Panel**: muestra/oculta el panel (no modal; se puede seguir modelando). Issues agrupados por severidad (Errores / Advertencias / Información).
- Al seleccionar un issue se selecciona y encuadra el elemento (`UIDocument.ShowElements`; en R04 se seleccionan ambos).
  Debajo: mensaje, explicación del BEP (de `rules.json`) y botones:
  - **Corregir** (texto = `fix.label`): `rename_type` (cuadro de texto), `set_parameter`
    (`user_input` → texto; `ai_suggestion` → `POST /ai/suggest-classification` y confirmación del `suggested_code`, con la tabla local si la IA no responde;
    `pick_list` → combo con los códigos Uniclass de la categoría), `join_geometry` (`JoinGeometryUtils.JoinGeometry`).
    Tras corregir se revalida y, si el issue ya existe en el backend, se hace `PATCH /issues/{id}` con `status=fixed`, `fixed_by=one_click`.
  - **Explicar con IA**: `POST /ai/explain`.
  - **No pude, ¿por qué?**: microencuesta (motivos de `FeedbackReason`) + comentario → `POST /feedback` con `element_guid` y `rule_id`.
- **Enviar al backend**: valida todo, arma `SnapshotCreate` en el hilo de Revit (`project_code` = primer segmento del nombre de archivo o `HKT`,
  `version_label` = `yyyyMMdd-HHmm`, `cde_state` del combo del panel, `rules_version`) y lo envía en segundo plano.
  Luego lee `GET /issues?snapshot_id=…&status=open` para conocer los ids que usará el PATCH.

## LISTA DE PRUEBA MANUAL (dentro de Revit 2027)

Preparación: proyecto nuevo con plantilla de arquitectura + estructura. Crear parámetros compartidos de proyecto:
`Uniclass_Codigo` (Texto, **tipo**) para Muros, Suelos, Puertas, Ventanas, Pilares/Armazón/Cimentación estructural;
`BIM_Material` (Texto, instancia) y `BIM_Resistencia_fc` (Texto, instancia) para las categorías de la §5 del BEP.
Guarda el archivo como `Prueba.rvt`. Backend levantado en `http://localhost:8000` salvo donde se indique.

| # | Paso | Resultado esperado |
|---|---|---|
| 0 | Abrir Revit con el add-in instalado | Pestaña **Profesor BIM** con 3 botones; sin errores al iniciar. |
| 1 | Pulsar **Panel** dos veces | El panel se muestra y se oculta. Con el panel abierto se puede seguir dibujando (no modal). |
| 2 | **R06** archivo: con `Prueba.rvt` pulsar **Validar todo** | Advertencia R06 «El archivo "Prueba" no sigue el patrón…». *Guardar como* `HKT-EQP-ZZ-ZZ-M3-S-0001.rvt` → R06 desaparece. |
| 3 | **R01** dibujar un muro con el tipo «Genérico - 200 mm» | Al soltar (≈0,6 s) aparece el error R01 sin pulsar nada (validación en vivo). |
| 4 | Fix R01: seleccionar el issue → **Renombrar tipo** → `MUR_CA_e25_FC210` | El tipo se renombra (Deshacer disponible: «Profesor BIM: renombrar tipo»); R01 desaparece para todas las instancias del tipo. |
| 5 | Seleccionar un issue de la lista | El elemento queda seleccionado y la vista se encuadra en él. |
| 6 | **R02** con el muro sin `Uniclass_Codigo` | Error R02 «…no tiene código Uniclass en "Uniclass_Codigo"». |
| 7 | Fix R02 (**Asignar código sugerido**) con backend arriba | Se muestra el código sugerido por la IA preseleccionado; al aceptar se escribe en el tipo; R02 desaparece. |
| 8 | Fix R02 con backend **apagado** | Mensaje «IA no disponible…»; aparece la lista local filtrada por categoría; se puede asignar igual. Revit no se congela. |
| 9 | **R03** escribir a mano `Ss_20_10_10` (código de columnas) en el tipo de muro | Error R03 «El código "Ss_20_10_10" no existe… o no corresponde a OST_Walls». |
| 10 | Fix R03 (**Elegir código válido**) | Combo solo con códigos de muros (Ss_25_10_20, Ss_25_10_30, Ss_25_10_50, Ss_20_05_65); al elegir, R03 desaparece. |
| 11 | **R05** pilar estructural sin `BIM_Material` ni `BIM_Resistencia_fc` | Dos advertencias R05, una por parámetro. |
| 12 | Fix R05 (**Completar parámetro**) → escribir `Concreto` / `210` | Cada advertencia desaparece al completar su parámetro. |
| 13 | **R07** viga cuyo nivel de referencia no exista / elemento sin nivel | Advertencia R07. (Asignar nivel a mano → desaparece.) |
| 14 | **R04** dibujar una viga que atraviese un muro sin unir | Advertencia R04 en el muro citando el UniqueId de la viga; al seleccionar se seleccionan ambos. |
| 15 | Fix R04 (**Unir geometría**) | Geometría unida; R04 desaparece. Con *Desunir* manualmente vuelve a aparecer. |
| 16 | Deshacer (Ctrl+Z) un fix | El issue correspondiente vuelve a aparecer tras el debounce. |
| 17 | Borrar un elemento con issues | Sus issues desaparecen del panel. |
| 18 | **Explicar con IA** en cualquier issue | Texto «IA: …» bajo la explicación; con backend apagado «IA no disponible: …». |
| 19 | **No pude, ¿por qué?** → elegir motivo + comentario → Aceptar | Estado «¡Gracias! Comentario registrado.»; en el backend `GET /feedback` muestra `element_guid`, `rule_id`, `reason`. |
| 20 | Elegir CDE `WIP` en el combo → **Enviar al backend** (ribbon o panel) | Estado «Snapshot #N enviado (HKT 2026…-…, WIP): X elementos, Y issues abiertos». `GET /snapshots` lo lista con `version_label` = fecha-hora. |
| 21 | Tras enviar, corregir un issue con 1 clic | Estado «Corregido y registrado en el backend (issue #id)»; `GET /issues?status=fixed` lo muestra con `fixed_by=one_click`. |
| 22 | Apagar el backend → **Enviar al backend**, **Explicar con IA**, **No pude** | Mensajes de estado de «sin conexión/Tiempo agotado»; Revit sigue respondiendo en todo momento (se puede orbitar/dibujar mientras espera). La validación local sigue funcionando. |
| 23 | Modelo con cientos de muros: mover/copiar varios muros seguidos | Sin pausas perceptibles al modelar; el panel se actualiza una vez al dejar de editar. |
| 24 | Cambiar a otro proyecto abierto | El panel pasa a mostrar los issues del documento activo. |
| 25 | Poner `"enabled": false` en una regla de `rules.json` (copia junto a la DLL) y reiniciar Revit | Esa regla deja de aparecer. |

## Limitaciones conocidas

- La validación en vivo se pausa si se cambia de documento: al activar otro documento se revalida completo.
- R06 se reevalúa en *Guardar como*; un archivo nuevo sin guardar se valida con su título («Proyecto1»).
- Para reglas de documento (R06) la microencuesta envía `element_guid = "DOC:<archivo>"` porque el contrato lo exige.
