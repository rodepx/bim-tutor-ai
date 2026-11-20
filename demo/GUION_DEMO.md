# Guion de demo — Agente Profesor BIM (5 minutos)

Público: jurado del hackathon (Reto 3: gestión de costos y presupuestos).
Roles: **P** = presentador (habla), **O** = operador (Revit y dashboard).

## Preparación (antes de subir al escenario)

```powershell
# 1. Backend (terminal 1)
cd C:\Users\Koco_Ghost\Documents\plugin\backend
.venv\Scripts\python -m uvicorn app.main:app --port 8000

# 2. Dashboard (terminal 2)
cd C:\Users\Koco_Ghost\Documents\plugin\frontend
npm run dev

# 3. Datos de respaldo: v1 sucia + v2 corregida + feedback (terminal 3)
cd C:\Users\Koco_Ghost\Documents\plugin
backend\.venv\Scripts\python.exe demo\seed.py
```

- Revit 2027 abierto con el modelo de demo y el panel del plugin acoplado a la derecha.
- Dashboard abierto en el navegador, en la pestaña **Salud**.
- Si no hay `LLM_API_KEY`, la IA corre en modo `mock` y la demo funciona igual.
- Ensayar una vez: el muro genérico se crea en el Nivel 1, entre ejes A y B, y cruza una viga existente.

---

## 0:00 – 0:40 · El problema

**P:** "En obra, el presupuesto sale del modelo. Si el modelo está sucio, el presupuesto está mal.
Un muro llamado *Genérico 200 mm* no dice si es de concreto o de ladrillo, y la diferencia es de
S/ 500 por m³ frente a S/ 85 por m². Un elemento sin código Uniclass no entra al metrado y
una viga que atraviesa un muro se cuenta dos veces. Hoy eso se descubre semanas después, cuando
el modelador ya pasó a otra cosa."

**P:** "Nuestro Agente Profesor BIM corrige el modelo mientras se dibuja y además explica cada error.
Con esos datos limpios arma el presupuesto 5D solo."

## 0:40 – 2:10 · En vivo en Revit

1. **O** dibuja un muro con el tipo de plantilla `Muro básico - Genérico 200 mm`.
   El panel muestra de inmediato **R01 Nombre de tipo genérico** y **R02 sin código Uniclass**.
   **P:** "Ni guardamos ni exportamos nada todavía. El plugin valida mientras se modela, con las
   reglas de `rules.json`, que salen del BEP."
2. **O** pulsa **¿Por qué?** en R01 y aparece la explicación didáctica con la referencia al BEP §3.
   **P:** "Por eso lo llamamos profesor: dice qué está mal y también por qué le importa a costos."
3. **O** renombra el tipo a `MUR_LAD_e15`. En R02 pulsa **Asignar código sugerido**: la IA propone
   `Ss_25_10_50 – Muros de albañilería` y **O** lo aplica con 1 clic.
   **P:** "La IA solo puede elegir entre los códigos válidos para la categoría Muros. Si inventa
   uno, el sistema lo descarta."
4. El panel marca **R04 Superposición muro–viga** (warning). **O** pulsa **Unir geometría**
   y el aviso desaparece.
   **P:** "Ese concreto se iba a pagar dos veces."
5. **O** abre un issue R05 de una columna (falta `BIM_Resistencia_fc`) y pulsa **No pude**.
   En la microencuesta elige *Falta información* y escribe "Estructuras no define f'c".
   **P:** "Si el modelador no puede corregir algo, nos dice por qué. Así el BIM Manager sabe si
   la regla está mal explicada o si falta un dato de otra disciplina."

## 2:10 – 2:30 · Envío al CDE

**O** pulsa **Enviar snapshot** en el panel. Toast: *v3 enviada, N issues abiertos*.
**P:** "Cada envío queda como una versión en el CDE según ISO 19650, y el backend guarda el historial."

## 2:30 – 3:30 · Dashboard

1. **Salud:** % de conformidad por disciplina (ARQ / EST), errores y avisos abiertos, issues por regla.
   **P:** "La v1 tenía 11 errores. La v2 tiene 0, por eso pudo pasar a SHARED. Si el modelo tiene
   errores, el backend no lo deja pasar (409)."
2. **Issues** → clic en el muro del eje 2 A-B → **Hilo del elemento**: se abrió en v1 por R04,
   recibió feedback de que no se entendía la regla y se cerró en v2.
3. **Recomendaciones:** se abre una de prioridad alta y se pulsa **ver datos**.
   **P:** "Cada número del texto viene de `facts`, calculado con SQL. La IA redacta, pero no
   inventa cifras."

## 3:30 – 4:20 · Presupuesto 5D y diferencia v1 → v2

1. **Presupuesto:** partidas con código de la Norma Técnica de Metrados, unidad, cantidad, P.U. y subtotal.
   Las partidas con precio sin validar aparecen marcadas. El estado CDE se muestra: *estimado* (no PUBLISHED).
   Bloque **No presupuestados** (sin código, código inválido…) y avisos de superposición.
2. **Diff v1 → v2:** total antes y después, partidas que cambian, elementos +3 / −1 / modificados.
   **P:** "En v1 siete elementos no entraban al presupuesto. Al corregirlos, el costo que faltaba
   ya aparece y queda trazado partida por partida."

## 4:20 – 4:40 · Exportes

**O** descarga **BCF** (abrir en un visor BCF o mostrar el .bcfzip), **CSV 4D** y **COBie .xlsx**.
**P:** "Funciona con herramientas que el equipo ya usa: BCF para coordinar, CSV para el 4D y
COBie para la entrega."

## 4:40 – 5:00 · Cierre e impacto

**P:** "Medimos tres cosas: el modelo se corrige mientras se dibuja, la mayoría de errores se
arreglan con 1 clic, y el presupuesto sale de datos limpios y trazables. La meta es que el
modelador aprenda el BEP usándolo, que el BIM Manager sepa qué reglas cuestan más y que el PM
tenga cifras en las que puede confiar. Gracias."

---

## Plan B sin Revit (si falla Revit o la laptop de demo)

`seed.py` simula el plugin: genera un edificio de 2 niveles con 56 elementos, siembra los
errores R01–R07, aplica las reglas de `data/rules.json` y envía v1 (WIP, con errores y archivo mal
nombrado) y v2 (corregida, archivo `HKT-EQP-ZZ-ZZ-M3-S-0001`). Además manda 6 respuestas de
microencuesta, marca un issue como corregido con 1 clic, prueba v1 → SHARED (debe dar 409) y
v2 → SHARED (debe aceptarse).

```powershell
cd C:\Users\Koco_Ghost\Documents\plugin
# con backend levantado
backend\.venv\Scripts\python.exe demo\seed.py
# otro servidor
backend\.venv\Scripts\python.exe demo\seed.py --base http://192.168.1.50:8000/api
# sin red: solo genera demo\out\v1.json, v2.json, feedback.json y muestra el resumen
backend\.venv\Scripts\python.exe demo\seed.py --dry-run
# pruebas
backend\.venv\Scripts\python.exe -m pytest demo -q
```

Guion B: el minuto 0:40–2:10 se reemplaza por capturas o un video corto del panel, y se ejecuta
`seed.py` en pantalla. La consola muestra en español cada paso, incluido el 409 de v1 y la
aceptación de v2. El resto del guion (dashboard, presupuesto, diff y exportes) queda igual.
Volver a ejecutar `seed.py` reemplaza v1 y v2 (son idempotentes por versión), pero el feedback
se acumula. Para empezar de cero, borrar la base SQLite del backend.

Elementos útiles para mostrar en el hilo (claves internas de `seed.py`):

| Elemento | Qué muestra |
|---|---|
| `LAD-N1-2-AB` (muro ladrillo N1, eje 2 A-B) | R04 en v1 + feedback "no entiendo la regla" → unido en v2 |
| `LAD-N1-1-AB` (muro N1, eje 1 A-B) | "Muro básico - Genérico 200 mm": R01+R02+R05 en v1 → `MUR_LAD_e15` en v2 |
| `ZAP-B1` (zapata B-1) | R02 corregido con 1 clic (sugerencia IA) |
| `VIG-N2-YB` (viga techo eje B) | R07 + feedback "error del plugin" |
| `LAD-N2-1-BC` | R04 que sigue abierto en v2 (warning, no bloquea SHARED) |
