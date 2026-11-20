# Checklist para el equipo de construcción — datos PENDIENTE VALIDAR

Todo lo que figura en `data/*.csv` y `docs/BEP.md` con la marca **PENDIENTE VALIDAR POR CONSTRUCCIÓN**
es un valor de ejemplo para la demo. Marca ✅ cuando esté validado, o corrige el valor en la columna
"Valor validado" y avisa al dueño de `data/`. **No cambies los códigos en los CSV sin coordinar**, porque
plugin, backend y tests los usan. Primero anota aquí la corrección.

Fuentes sugeridas:
- **Uniclass:** tabla oficial Uniclass 2015 – Ss (NBS, uniclass.thenbs.com), versión vigente.
- **Partidas:** Norma Técnica "Metrados para Obras de Edificación y Habilitaciones Urbanas" (MVCS, RM 073-2010-VIVIENDA, verificar vigencia).
- **Precios unitarios:** revista *Costos* (edición del mes), índices y boletines CAPECO, APU propio de la empresa, cotizaciones de proveedores. Todos sin IGV y en PEN.
- **Ratios de acero y encofrado:** metrados de proyectos similares de la empresa o el promedio de los planos de estructuras.

## 1. Códigos Uniclass (`data/uniclass_subset.csv`)

| ✓ | Código | Título (es) | Categorías Revit | Qué validar | Valor validado |
|---|---|---|---|---|---|
| ☐ | Ss_20_05_15 | Cimentación de concreto armado (zapatas) | OST_StructuralFoundation | Que el código y su título existan en la tabla oficial | |
| ☐ | Ss_20_05_65 | Cimiento corrido | OST_StructuralFoundation; OST_Walls | ¿Se permite que sea un muro? (cimiento modelado como muro) | |
| ☐ | Ss_20_10_10 | Columnas de concreto armado | OST_StructuralColumns | Código oficial | |
| ☐ | Ss_20_10_20 | Vigas de concreto armado | OST_StructuralFraming | Código oficial | |
| ☐ | Ss_20_10_75 | Estructura de acero | OST_StructuralFraming; OST_StructuralColumns | Código oficial. Ver nota A (f'c en acero) | |
| ☐ | Ss_25_10_20 | Muros de concreto armado (placas) | OST_Walls | Código oficial | |
| ☐ | Ss_25_10_50 | Muros de albañilería | OST_Walls | Código oficial | |
| ☐ | Ss_25_10_30 | Tabiquería ligera (drywall) | OST_Walls | Código oficial | |
| ☐ | Ss_30_10_30 | Losa maciza de concreto | OST_Floors | Código oficial | |
| ☐ | Ss_30_10_35 | Losa aligerada | OST_Floors | Código oficial. La losa aligerada con ladrillo de techo es típica de Perú; ¿hay un código Ss más preciso? | |
| ☐ | Ss_25_30_20 | Puertas | OST_Doors | Código oficial | |
| ☐ | Ss_25_30_95 | Ventanas | OST_Windows | Código oficial | |
| ☐ | — | Faltantes | — | ¿Hace falta agregar escaleras, cimiento armado, sobrecimiento, vigas de cimentación o contrapiso? | |

## 2. Partidas, unidades y factores (`data/mapeo_partidas.csv`)

Cantidad = magnitud del elemento × factor (BEP §8). Revisa la numeración, la redacción según la norma, la unidad y el factor.

| ✓ | Uniclass | Partida | Descripción | Unidad | Magnitud × factor | Qué validar | Valor validado |
|---|---|---|---|---|---|---|---|
| ☐ | Ss_20_05_15 | OE.2.3.3.1 | Concreto f'c=210 kg/cm2 en zapatas | m3 | volume × 1.00 | Numeración y f'c | |
| ☐ | Ss_20_05_15 | OE.2.3.3.2 | Acero fy=4200 kg/cm2 en zapatas | kg | volume × 50 | Ratio 50 kg/m³. ¿Lleva encofrado? Si lo lleva, el acero sería .3 | |
| ☐ | Ss_20_05_65 | OE.2.2.2.1 | Concreto ciclópeo 1:10+30% PG en cimiento corrido | m3 | volume × 1.00 | Numeración (concreto simple) y dosificación | |
| ☐ | Ss_20_10_10 | OE.2.3.6.1 | Concreto f'c=210 en columnas | m3 | volume × 1.00 | Numeración | |
| ☐ | Ss_20_10_10 | OE.2.3.6.2 | Encofrado y desencofrado en columnas | m2 | volume × 10 | 10 m²/m³ corresponde a 40×40 (perímetro/sección). Para otras secciones el ratio cambia | |
| ☐ | Ss_20_10_10 | OE.2.3.6.3 | Acero fy=4200 en columnas | kg | volume × 120 | Ratio | |
| ☐ | Ss_20_10_20 | OE.2.3.7.1 | Concreto f'c=210 en vigas | m3 | volume × 1.00 | Numeración | |
| ☐ | Ss_20_10_20 | OE.2.3.7.2 | Encofrado y desencofrado en vigas | m2 | volume × 8 | Para 25×50 con fondo y 2 costados el ratio es ≈10, y descontando la losa ≈7. Confirmar | |
| ☐ | Ss_20_10_20 | OE.2.3.7.3 | Acero fy=4200 en vigas | kg | volume × 110 | Ratio | |
| ☐ | Ss_20_10_75 | OE.2.5.1.1 | Estructura metálica de acero A36 | kg | volume × 7850 | Densidad correcta. Validar numeración y si se incluyen pintura y conexiones | |
| ☐ | Ss_25_10_20 | OE.2.3.5.1 | Concreto f'c=210 en placas | m3 | volume × 1.00 | Numeración | |
| ☐ | Ss_25_10_20 | OE.2.3.5.2 | Encofrado y desencofrado en placas | m2 | area × 2.00 | Dos caras: correcto si `area_m2` es el área de una sola cara | |
| ☐ | Ss_25_10_20 | — | **Falta: acero en placas** | kg | volume × ? | Propuesta: agregar OE.2.3.5.3 (ratio ~80–100 kg/m³). Ver nota B | |
| ☐ | Ss_25_10_50 | OE.3.1.1.1 | Muro de ladrillo King Kong de soga | m2 | area × 1.00 | Redacción sugerida: "Muro de ladrillo KK de arcilla de soga, mortero C:A 1:4". Confirmar soga o cabeza según e=15 | |
| ☐ | Ss_25_10_30 | OE.3.1.3.1 | Tabique de drywall e=15 cm | m2 | area × 1.00 | El drywall no está en OE.3.1 de la norma (albañilería). Definir la partida y el espesor típico (10–12 cm) | |
| ☐ | Ss_30_10_30 | OE.2.3.8.1 | Concreto f'c=210 en losa maciza | m3 | volume × 1.00 | **Faltan el encofrado (m²) y el acero (kg) de la losa maciza.** Ver nota B | |
| ☐ | Ss_30_10_35 | OE.2.3.9.1 | Losa aligerada h=20 cm (concreto + ladrillo + acero) | m2 | area × 1.00 | La norma metra la losa aligerada por separado (concreto m³, encofrado m², acero kg, ladrillo und). Esta partida compuesta por m² es tipo APU. Decidir cuál usar | |
| ☐ | Ss_25_30_20 | OE.3.9.1.1 | Puerta contraplacada de madera | und | count × 1 | Numeración (carpintería de madera). ¿und o m²? | |
| ☐ | Ss_25_30_95 | OE.3.10.1.1 | Ventana de aluminio con vidrio simple | m2 | area × 1.00 | Numeración (carpintería metálica/aluminio). `area_m2` = ancho × alto del vano | |

## 3. Precios unitarios (PEN, sin IGV)

| ✓ | Partida | P.U. ejemplo | Fuente sugerida | P.U. validado | Fuente / fecha |
|---|---|---|---|---|---|
| ☐ | OE.2.3.3.1 Concreto zapatas | 480.00 /m3 | APU propio / revista Costos | | |
| ☐ | OE.2.3.3.2 Acero zapatas | 5.20 /kg | Cotización acero corrugado + MO (CAPECO) | | |
| ☐ | OE.2.2.2.1 Concreto ciclópeo | 290.00 /m3 | revista Costos | | |
| ☐ | OE.2.3.6.1 Concreto columnas | 520.00 /m3 | APU propio | | |
| ☐ | OE.2.3.6.2 Encofrado columnas | 58.00 /m2 | APU propio | | |
| ☐ | OE.2.3.6.3 Acero columnas | 5.20 /kg | Cotización + MO | | |
| ☐ | OE.2.3.7.1 Concreto vigas | 510.00 /m3 | APU propio | | |
| ☐ | OE.2.3.7.2 Encofrado vigas | 62.00 /m2 | APU propio | | |
| ☐ | OE.2.3.7.3 Acero vigas | 5.20 /kg | Cotización + MO | | |
| ☐ | OE.2.5.1.1 Estructura metálica | 9.50 /kg | Cotización fabricante | | |
| ☐ | OE.2.3.5.1 Concreto placas | 500.00 /m3 | APU propio | | |
| ☐ | OE.2.3.5.2 Encofrado placas | 55.00 /m2 | APU propio | | |
| ☐ | OE.3.1.1.1 Muro KK soga | 85.00 /m2 | revista Costos | | |
| ☐ | OE.3.1.3.1 Tabique drywall | 95.00 /m2 | Cotización instalador | | |
| ☐ | OE.2.3.8.1 Concreto losa maciza | 495.00 /m3 | APU propio | | |
| ☐ | OE.2.3.9.1 Losa aligerada h=20 | 165.00 /m2 | APU propio / revista Costos | | |
| ☐ | OE.3.9.1.1 Puerta contraplacada | 650.00 /und | Cotización carpintero | | |
| ☐ | OE.3.10.1.1 Ventana aluminio | 280.00 /m2 | Cotización proveedor | | |

## 4. LOIN (`docs/BEP.md` §5 y R05 en `data/rules.json`)

| ✓ | Ítem | Valor actual | Qué validar | Valor validado |
|---|---|---|---|---|
| ☐ | Parámetro `BIM_Material` | Texto libre | ¿Debe ser una lista cerrada (Concreto armado, Albañilería KK, Drywall…)? | |
| ☐ | Parámetro `BIM_Resistencia_fc` | Texto, kg/cm² (`210`) | Unidad, formato y valores permitidos (175/210/280/350) | |
| ☐ | Categorías con f'c obligatorio | Columnas, vigas, cimentación | Ver nota A: también se exige a elementos de acero | |
| ☐ | Etapa LOIN | Diseño de detalle (≈LOD 300) | ¿Es la etapa correcta para el presupuesto que se presenta? | |
| ☐ | Puertas y ventanas | Solo `Uniclass_Codigo` | ¿Hace falta material o tipo de vidrio para elegir el P.U.? | |

## 5. Nombres de tipo (`docs/BEP.md` §3, R01)

| ✓ | Ítem | Valor actual | Qué validar |
|---|---|---|---|
| ☐ | Patrón | `CAT_MATERIAL_DIMENSION[_DETALLE]` | ¿Es aceptado por el equipo? |
| ☐ | Prefijos | MUR, COL, VIG, LOS, ZAP, PTA, VEN | ¿Faltan otros (ESC, CIM, SOB, CTP…)? |
| ☐ | Materiales | CA, LAD, DRY, ALIG, MAC, MAD, ALU | Lista cerrada de abreviaturas |
| ☐ | Patrones prohibidos | genérico, default, básico, `tipo N`, copia, terminado en ` N` | Hay riesgo de falsos positivos: un tipo legítimo que termine en espacio + número |

## Notas para el equipo técnico

- **A. f'c en acero.** R05 pide `BIM_Resistencia_fc` a toda `OST_StructuralFraming/Columns`, incluidas
  las de acero (`Ss_20_10_75`). Una viga metálica no tiene f'c, así que siempre dará aviso o el modelador
  pondrá un valor de relleno. Hay que decidir si se excluye por código o se usa otro parámetro (fy). Es un
  cambio de regla y lo decide el dueño de `rules.json`.
- **B. Partidas faltantes.** Faltan el acero de las placas y el encofrado y acero de la losa maciza. Por eso
  el presupuesto 5D queda subestimado en esos elementos. No agregamos estas filas para no mover los
  totales que usan los tests del backend. Si se validan, se agregan como filas nuevas con estado
  PENDIENTE VALIDAR POR CONSTRUCCIÓN.
- **C. Superposiciones.** El presupuesto no descuenta el volumen duplicado de R04 y solo lo informa
  (`overlap_warnings`). La corrección real es unir la geometría en Revit.
