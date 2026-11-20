# BEP mínimo — Proyecto Hackathon (HKT)

> Basado en NTP-ISO 19650-1/2/4 y clasificación Uniclass 2015. Versión 0.1 — **PENDIENTE VALIDAR POR CONSTRUCCIÓN**.
> Cada regla de `data/rules.json` cita la sección de este documento que la origina (`bep_ref`).

## 1. Roles

| Rol | Código | Responsabilidad |
|---|---|---|
| Parte que designa (cliente) | CLI | Define requisitos de información (EIR) |
| Parte designada principal | EQP | Coordina, aprueba paso SHARED → PUBLISHED |
| BIM Manager | BIM | Mantiene el BEP y `rules.json` |
| Modelador Arquitectura | A | Modelo ARQ |
| Modelador Estructuras | S | Modelo EST |
| Modelador Instalaciones | M | Modelo MEP |
| Costos / PM | Q | Presupuesto 5D, recomendaciones |

## 2. Naming de archivos (§2)

Patrón ISO 19650: `Proyecto-Originador-Volumen-Nivel-Tipo-Rol-Número`

| Campo | Valores | Ejemplo |
|---|---|---|
| Proyecto | 2–6 caracteres A-Z/0-9 | `HKT` |
| Originador | 2–6 caracteres | `EQP` |
| Volumen/Sistema | 2 caracteres, `ZZ` = todos | `ZZ` |
| Nivel | 2 caracteres, `ZZ` = varios | `ZZ` |
| Tipo | `M3` = modelo 3D | `M3` |
| Rol | 1–2 letras (tabla §1) | `S` |
| Número | 4 dígitos | `0001` |

Ejemplo válido: `HKT-EQP-ZZ-ZZ-M3-S-0001.rvt`
Regex: `^[A-Z0-9]{2,6}-[A-Z0-9]{2,6}-[A-Z0-9]{2}-[A-Z0-9]{2}-M3-[A-Z]{1,2}-\d{4}$` (sin extensión).

## 3. Naming de tipos (§3)

Patrón: `CAT_MATERIAL_DIMENSION[_DETALLE]`, en mayúsculas, sin espacios.

| Categoría | CAT | Ejemplo |
|---|---|---|
| Muros | `MUR` | `MUR_CA_e25_FC210`, `MUR_LAD_e15` |
| Columnas | `COL` | `COL_CA_40x40_FC210` |
| Vigas | `VIG` | `VIG_CA_25x50_FC210` |
| Losas / Suelos | `LOS` | `LOS_ALIG_e20`, `LOS_MAC_e20_FC210` |
| Zapatas / Cimentación | `ZAP` | `ZAP_CA_150x150x60_FC210` |
| Puertas | `PTA` | `PTA_MAD_090x210` |
| Ventanas | `VEN` | `VEN_ALU_120x150` |

Prohibido: nombres genéricos de plantilla (`Genérico`, `Generic`, `Default`, `Básico`, `Muro básico`, `Tipo 1`, `Copia`, nombres terminados en ` 2`, ` 3`…).

## 4. Clasificación (§4)

- Todo elemento de las categorías de la §3 lleva el parámetro compartido **`Uniclass_Codigo`** (texto, de tipo).
  Si no existe, el plugin también lee `Classification.Uniclass.Ss.Number`.
- Tabla usada: Uniclass 2015 **Ss (Sistemas)**, subconjunto en `data/uniclass_subset.csv`.
- El código debe existir en esa tabla y corresponder a la categoría Revit del elemento.

## 5. LOIN — Nivel de Información Necesario (§5)

Etapa: diseño de detalle (equivalente LOD 300). Parámetros obligatorios por categoría:

| Categoría | Parámetros obligatorios |
|---|---|
| Muros | `Uniclass_Codigo`, `BIM_Material` |
| Columnas estructurales | `Uniclass_Codigo`, `BIM_Material`, `BIM_Resistencia_fc` |
| Armazón estructural (vigas) | `Uniclass_Codigo`, `BIM_Material`, `BIM_Resistencia_fc` |
| Suelos / Losas | `Uniclass_Codigo`, `BIM_Material` |
| Cimentación estructural | `Uniclass_Codigo`, `BIM_Material`, `BIM_Resistencia_fc` |
| Puertas / Ventanas | `Uniclass_Codigo` |

`Uniclass_Codigo` se verifica con R02/R03; `BIM_Material` y `BIM_Resistencia_fc` con R05.
`BIM_Resistencia_fc` se registra en kg/cm² como texto numérico (p. ej. `210`).

Geometría: todo elemento asociado a un **nivel** (necesario para 4D y metrados por piso).
Puertas y ventanas toman el nivel de su muro anfitrión, por eso R07 no las revisa.

## 6. Coordinación (§6)

- Muros y vigas no deben superponerse sin unión de geometría (Join/Cut): la superposición duplica volúmenes
  de concreto en el metrado.
- Detección en el plugin con `ElementIntersectsElementFilter`; corrección con `JoinGeometryUtils`.

## 7. CDE — Entorno Común de Datos (§7)

| Estado | Significado | Quién lo mueve | Condición |
|---|---|---|---|
| WIP | Trabajo en curso del equipo | Modelador | — |
| SHARED | Compartido para coordinación | Modelador → BIM | 0 issues `error` abiertos |
| PUBLISHED | Aprobado para uso contractual / presupuesto oficial | EQP | Revisado por BIM y Q |
| ARCHIVED | Versión histórica | BIM | Reemplazado por nueva PUBLISHED |

Cada envío del plugin al backend es un **snapshot** con su estado CDE. El presupuesto oficial solo se toma de PUBLISHED;
los de WIP/SHARED son estimados.

## 8. Presupuesto 5D (§8)

- Moneda: PEN (S/), precios sin IGV.
- Partidas según la Norma Técnica "Metrados para Obras de Edificación y Habilitaciones Urbanas" (MVCS), con
  mapeo en `data/mapeo_partidas.csv`. La numeración `OE.x.x.x.x` es de ejemplo y está pendiente de validación
  (ver `demo/VALIDAR_CONSTRUCCION.md`).
- Cantidad = magnitud del elemento (`volume_m3`, `area_m2`, `length_m` o `count` = 1 por elemento) × `factor` de la partida.
  El factor permite derivar acero (kg/m3) y encofrado (m2/m3) del volumen; son ratios de ejemplo a validar.
- Un código Uniclass puede generar varias partidas (concreto + encofrado + acero).
- Cada elemento (UniqueId) se cuenta una sola vez por partida.
- Elementos sin código válido quedan como "no presupuestados" y se reportan.
