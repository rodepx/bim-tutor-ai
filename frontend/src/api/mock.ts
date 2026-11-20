// Datos de demostración tipados con el contrato (contracts/openapi.yaml).
// Escenario: proyecto HKT, v1 en WIP con errores; v2 corregida y en SHARED.
// Partidas y precios tomados de data/mapeo_partidas.csv.
import {
  ApiError,
  type ApiClient,
  type Budget,
  type BudgetDiff,
  type BudgetDiffLine,
  type BudgetLine,
  type CdeState,
  type Discipline,
  type Element,
  type ElementThread,
  type Feedback,
  type Issue,
  type IssueFilters,
  type Recommendation,
  type RuleStats,
  type Snapshot,
  type Stats,
  type ThreadEvent,
  type Unit,
} from "./types";
import { RULE_NAMES } from "../rules";
import { formatPEN } from "../format";

const round2 = (n: number) => Math.round(n * 100) / 100;
const guid = (n: number) =>
  `8a1f3c2e-5b7d-4e9a-b1c4-0f6d2e9a${(0x3c00 + n).toString(16)}-000${(0x4a100 + n * 37).toString(16)}`;

// ---------------------------------------------------------------- snapshots
const SNAPSHOT_DATES: Record<number, string> = {
  1: "2026-11-17T15:20:00Z",
  2: "2026-11-18T21:45:00Z",
};

const ELEMENT_COUNTS: Record<number, Record<"ARQ" | "EST", number>> = {
  1: { ARQ: 94, EST: 48 },
  2: { ARQ: 99, EST: 52 },
};

function initialSnapshots(): Snapshot[] {
  return [
    {
      id: 2,
      project_code: "HKT",
      file_name: "HKT-EQP-ZZ-ZZ-M3-A-0001",
      version_label: "v2",
      cde_state: "SHARED",
      rules_version: "0.1.0",
      author: "Modelador ARQ",
      created_at: SNAPSHOT_DATES[2],
      element_count: 151,
      open_issue_count: 0, // se recalcula
    },
    {
      id: 1,
      project_code: "HKT",
      file_name: "HKT_Arquitectura_final2",
      version_label: "v1",
      cde_state: "WIP",
      rules_version: "0.1.0",
      author: "Modelador ARQ",
      created_at: SNAPSHOT_DATES[1],
      element_count: 142,
      open_issue_count: 0,
    },
  ];
}

// ---------------------------------------------------------------- elementos
// Estado de cada elemento en la última versión (v2); los mensajes de issues reflejan cómo estaban en v1.
const ELEMENTS: Element[] = [
  { guid: guid(1), element_id: 312455, category: "OST_Walls", discipline: "ARQ", family_name: "Muro básico", type_name: "MUR_LAD_e20", classification_code: "Ss_25_10_50", level: "Nivel 1", volume_m3: 2.4, area_m2: 12.0, length_m: 4.8, parameters: { BIM_Material: "Ladrillo KK" } },
  { guid: guid(2), element_id: 312490, category: "OST_Walls", discipline: "ARQ", family_name: "Muro básico", type_name: "MUR_CA_e30_FC210", classification_code: "Ss_25_10_20", level: "Nivel 2", volume_m3: 3.15, area_m2: 10.5, length_m: 3.5, parameters: { BIM_Material: "Concreto" } },
  { guid: guid(3), element_id: 318002, category: "OST_StructuralColumns", discipline: "EST", family_name: "M_Columna-Rectangular", type_name: "COL_CA_40x40_FC210", classification_code: "Ss_20_10_10", level: "Nivel 1", volume_m3: 0.48, area_m2: null, length_m: 3.0, parameters: { BIM_Material: "Concreto", BIM_Resistencia_fc: "210" } },
  { guid: guid(4), element_id: 312611, category: "OST_Walls", discipline: "ARQ", family_name: "Muro básico", type_name: "MUR_LAD_e15", classification_code: "Ss_25_10_50", level: "Nivel 1", volume_m3: 1.62, area_m2: 10.8, length_m: 4.2, parameters: { BIM_Material: "Ladrillo KK" } },
  { guid: guid(5), element_id: 320114, category: "OST_Floors", discipline: "ARQ", family_name: "Suelo", type_name: "LOS_ALIG_e20", classification_code: "Ss_30_10_35", level: "Nivel 2", volume_m3: 9.8, area_m2: 49.0, length_m: null, parameters: { BIM_Material: "Aligerado" } },
  { guid: guid(6), element_id: 325870, category: "OST_Doors", discipline: "ARQ", family_name: "Puerta simple", type_name: "PTA_MAD_090x210", classification_code: "Ss_25_30_20", level: "Nivel 1", volume_m3: null, area_m2: 1.89, length_m: null, parameters: {} },
  { guid: guid(7), element_id: 319340, category: "OST_StructuralFraming", discipline: "EST", family_name: "M_Viga-Rectangular", type_name: "VIG_CA_25x50_FC210", classification_code: "Ss_20_10_20", level: "Nivel 2", volume_m3: 0.75, area_m2: null, length_m: 6.0, parameters: { BIM_Material: "Concreto", BIM_Resistencia_fc: "210" } },
  { guid: guid(8), element_id: 312702, category: "OST_Walls", discipline: "ARQ", family_name: "Muro básico", type_name: "MUR_CA_e25_FC210", classification_code: "Ss_25_10_20", level: "Nivel 1", volume_m3: 2.75, area_m2: 11.0, length_m: 4.4, parameters: { BIM_Material: "Concreto" } },
  { guid: guid(9), element_id: 326001, category: "OST_Windows", discipline: "ARQ", family_name: "Ventana fija", type_name: "VEN_ALU_120x150", classification_code: "Ss_20_10_10", level: "Nivel 2", volume_m3: null, area_m2: 1.8, length_m: null, parameters: {} },
  { guid: guid(10), element_id: 312810, category: "OST_Walls", discipline: "ARQ", family_name: "Muro básico", type_name: "MUR_CA_e25_FC210", classification_code: "Ss_25_10_20", level: "Nivel 2", volume_m3: 3.0, area_m2: 12.0, length_m: 4.8, parameters: { BIM_Material: "Concreto" } },
  { guid: guid(11), element_id: 319355, category: "OST_StructuralFraming", discipline: "EST", family_name: "M_Viga-Rectangular", type_name: "VIG_CA_25x50_FC210", classification_code: "Ss_20_10_20", level: "Nivel 2", volume_m3: 0.6, area_m2: null, length_m: 4.8, parameters: { BIM_Material: "Concreto", BIM_Resistencia_fc: "210" } },
  { guid: guid(12), element_id: 312833, category: "OST_Walls", discipline: "ARQ", family_name: "Muro básico", type_name: "MUR_CA_e25_FC210", classification_code: "Ss_25_10_20", level: "Nivel 1", volume_m3: 2.5, area_m2: 10.0, length_m: 4.0, parameters: { BIM_Material: "Concreto" } },
  { guid: guid(13), element_id: 319362, category: "OST_StructuralFraming", discipline: "EST", family_name: "M_Viga-Rectangular", type_name: "VIG_CA_30x60_FC210", classification_code: "Ss_20_10_20", level: "Nivel 1", volume_m3: 0.9, area_m2: null, length_m: 5.0, parameters: { BIM_Material: "Concreto", BIM_Resistencia_fc: "210" } },
  { guid: guid(14), element_id: 312850, category: "OST_Walls", discipline: "ARQ", family_name: "Muro básico", type_name: "MUR_CA_e25_FC210", classification_code: "Ss_25_10_20", level: "Nivel 2", volume_m3: 2.25, area_m2: 9.0, length_m: 3.6, parameters: { BIM_Material: "Concreto" } },
  { guid: guid(15), element_id: 318040, category: "OST_StructuralColumns", discipline: "EST", family_name: "M_Columna-Rectangular", type_name: "COL_CA_40x40_FC210", classification_code: "Ss_20_10_10", level: "Nivel 1", volume_m3: 0.48, area_m2: null, length_m: 3.0, parameters: { BIM_Material: "Concreto", BIM_Resistencia_fc: null } },
  { guid: guid(16), element_id: 317011, category: "OST_StructuralFoundation", discipline: "EST", family_name: "Zapata aislada", type_name: "ZAP_CA_150x150x60_FC210", classification_code: "Ss_20_05_15", level: "Cimentación", volume_m3: 1.35, area_m2: null, length_m: null, parameters: { BIM_Material: null, BIM_Resistencia_fc: "210" } },
  { guid: guid(17), element_id: 320150, category: "OST_Floors", discipline: "ARQ", family_name: "Suelo", type_name: "LOS_MAC_e20_FC210", classification_code: "Ss_30_10_30", level: "Nivel 1", volume_m3: 3.6, area_m2: 18.0, length_m: null, parameters: { BIM_Material: null } },
  { guid: guid(18), element_id: 319401, category: "OST_StructuralFraming", discipline: "EST", family_name: "M_Viga-Rectangular", type_name: "VIG_CA_25x40_FC210", classification_code: "Ss_20_10_20", level: "Nivel 3", volume_m3: 0.5, area_m2: null, length_m: 5.0, parameters: { BIM_Material: null, BIM_Resistencia_fc: null } },
  { guid: guid(19), element_id: 312900, category: "OST_Walls", discipline: "ARQ", family_name: "Muro básico", type_name: "MUR_LAD_e15", classification_code: "Ss_25_10_50", level: "Nivel 1", volume_m3: 1.35, area_m2: 9.0, length_m: 3.0, parameters: { BIM_Material: "Ladrillo KK" } },
  { guid: guid(20), element_id: 318077, category: "OST_StructuralColumns", discipline: "EST", family_name: "M_Columna-Rectangular", type_name: "COL_CA_40x40_FC210", classification_code: "Ss_20_10_10", level: null, volume_m3: 0.48, area_m2: null, length_m: 3.0, parameters: { BIM_Material: "Concreto", BIM_Resistencia_fc: "210" } },
  { guid: guid(21), element_id: 312955, category: "OST_Walls", discipline: "ARQ", family_name: "Muro básico", type_name: "MUR_LAD_e15", classification_code: "Ss_25_10_50", level: "Nivel 3", volume_m3: 1.2, area_m2: 8.0, length_m: 3.2, parameters: { BIM_Material: "Ladrillo KK" } },
  { guid: guid(22), element_id: 317090, category: "OST_StructuralFoundation", discipline: "EST", family_name: "Cimiento corrido", type_name: "ZAP_CC_060x080", classification_code: "Ss_20_05_65", level: null, volume_m3: 2.4, area_m2: null, length_m: 5.0, parameters: { BIM_Material: "Concreto ciclópeo", BIM_Resistencia_fc: null } },
];
const ELEMENT_BY_GUID = new Map(ELEMENTS.map((e) => [e.guid, e]));

// ---------------------------------------------------------------- issues
interface MockIssue {
  id: number;
  rule_id: string;
  severity: Issue["severity"];
  element_guid: string | null;
  related_guid?: string | null;
  message: string;
  opened_in: number;
  closed_in?: number;
  closed_as?: "fixed" | "dismissed";
  fixed_by?: "one_click" | "manual";
  resolved_at?: string;
}

const T = (snap: number, minutes: number) =>
  new Date(Date.parse(SNAPSHOT_DATES[snap]) + minutes * 60_000).toISOString();

const MOCK_ISSUES: MockIssue[] = [
  // R01 — nombre genérico (error)
  { id: 101, rule_id: "R01", severity: "error", element_guid: guid(1), message: 'El tipo "Muro básico 200mm" tiene un nombre genérico de plantilla.', opened_in: 1, closed_in: 2, closed_as: "fixed", fixed_by: "manual", resolved_at: T(2, -180) },
  { id: 102, rule_id: "R01", severity: "error", element_guid: guid(2), message: 'El tipo "Genérico - 300mm" tiene un nombre genérico de plantilla.', opened_in: 1, closed_in: 2, closed_as: "fixed", fixed_by: "manual", resolved_at: T(2, -170) },
  { id: 103, rule_id: "R01", severity: "error", element_guid: guid(3), message: 'El tipo "Copia de COL 2" tiene un nombre genérico de plantilla.', opened_in: 1, closed_in: 2, closed_as: "fixed", fixed_by: "manual", resolved_at: T(2, -160) },
  // R02 — sin código (error)
  { id: 104, rule_id: "R02", severity: "error", element_guid: guid(4), message: 'El elemento no tiene código Uniclass en "Uniclass_Codigo".', opened_in: 1, closed_in: 2, closed_as: "fixed", fixed_by: "one_click", resolved_at: T(2, -150) },
  { id: 105, rule_id: "R02", severity: "error", element_guid: guid(5), message: 'El elemento no tiene código Uniclass en "Uniclass_Codigo".', opened_in: 1, closed_in: 2, closed_as: "fixed", fixed_by: "one_click", resolved_at: T(2, -148) },
  { id: 106, rule_id: "R02", severity: "error", element_guid: guid(6), message: 'El elemento no tiene código Uniclass en "Uniclass_Codigo".', opened_in: 1, closed_in: 2, closed_as: "fixed", fixed_by: "one_click", resolved_at: T(2, -146) },
  { id: 107, rule_id: "R02", severity: "error", element_guid: guid(7), message: 'El elemento no tiene código Uniclass en "Uniclass_Codigo".', opened_in: 1, closed_in: 2, closed_as: "fixed", fixed_by: "manual", resolved_at: T(2, -120) },
  { id: 120, rule_id: "R02", severity: "error", element_guid: guid(2), message: 'El elemento no tiene código Uniclass en "Uniclass_Codigo".', opened_in: 1, closed_in: 2, closed_as: "fixed", fixed_by: "one_click", resolved_at: T(2, -165) },
  // R03 — código inválido (error)
  { id: 108, rule_id: "R03", severity: "error", element_guid: guid(8), message: 'El código "Ss_25_10_99" no existe en la tabla Uniclass del proyecto o no corresponde a OST_Walls.', opened_in: 1, closed_in: 2, closed_as: "fixed", fixed_by: "one_click", resolved_at: T(2, -110) },
  { id: 109, rule_id: "R03", severity: "error", element_guid: guid(9), message: 'El código "Ss_20_10_10" no existe en la tabla Uniclass del proyecto o no corresponde a OST_Windows.', opened_in: 1, closed_in: 2, closed_as: "dismissed", resolved_at: T(2, -100) },
  // R04 — superposición (warning)
  { id: 110, rule_id: "R04", severity: "warning", element_guid: guid(10), related_guid: guid(11), message: `El elemento se superpone con ${guid(11)} sin unión de geometría.`, opened_in: 1, closed_in: 2, closed_as: "fixed", fixed_by: "one_click", resolved_at: T(2, -90) },
  { id: 111, rule_id: "R04", severity: "warning", element_guid: guid(12), related_guid: guid(13), message: `El elemento se superpone con ${guid(13)} sin unión de geometría.`, opened_in: 1 },
  { id: 112, rule_id: "R04", severity: "warning", element_guid: guid(14), related_guid: guid(7), message: `El elemento se superpone con ${guid(7)} sin unión de geometría.`, opened_in: 1 },
  // R05 — LOIN (warning)
  { id: 113, rule_id: "R05", severity: "warning", element_guid: guid(15), message: 'Falta el parámetro "BIM_Resistencia_fc" exigido por el LOIN.', opened_in: 1 },
  { id: 114, rule_id: "R05", severity: "warning", element_guid: guid(16), message: 'Falta el parámetro "BIM_Material" exigido por el LOIN.', opened_in: 1 },
  { id: 115, rule_id: "R05", severity: "warning", element_guid: guid(17), message: 'Falta el parámetro "BIM_Material" exigido por el LOIN.', opened_in: 1 },
  { id: 116, rule_id: "R05", severity: "warning", element_guid: guid(2), message: 'Falta el parámetro "BIM_Material" exigido por el LOIN.', opened_in: 1, closed_in: 2, closed_as: "fixed", fixed_by: "manual", resolved_at: T(2, -140) },
  { id: 117, rule_id: "R05", severity: "warning", element_guid: guid(18), message: 'Falta el parámetro "BIM_Material" exigido por el LOIN.', opened_in: 2 },
  { id: 123, rule_id: "R05", severity: "warning", element_guid: guid(21), message: 'Falta el parámetro "BIM_Material" exigido por el LOIN.', opened_in: 1, closed_in: 2, closed_as: "fixed", fixed_by: "manual", resolved_at: T(2, -60) },
  // R06 — nombre de archivo (warning, documento)
  { id: 118, rule_id: "R06", severity: "warning", element_guid: null, message: 'El archivo "HKT_Arquitectura_final2" no sigue el patrón Proyecto-Originador-Volumen-Nivel-Tipo-Rol-Número.', opened_in: 1, closed_in: 2, closed_as: "fixed", fixed_by: "manual", resolved_at: T(2, -30) },
  // R07 — sin nivel (warning)
  { id: 119, rule_id: "R07", severity: "warning", element_guid: guid(19), message: "El elemento no está asociado a un nivel.", opened_in: 1, closed_in: 2, closed_as: "fixed", fixed_by: "manual", resolved_at: T(2, -50) },
  { id: 121, rule_id: "R07", severity: "warning", element_guid: guid(20), message: "El elemento no está asociado a un nivel.", opened_in: 1 },
  { id: 122, rule_id: "R07", severity: "warning", element_guid: guid(22), message: "El elemento no está asociado a un nivel.", opened_in: 2 },
];

function disciplineOf(g: string | null | undefined): Discipline | null {
  return g ? ELEMENT_BY_GUID.get(g)?.discipline ?? null : null;
}

/** Estado de cada issue tal como se veía en el snapshot dado. */
function issuesAt(snapshotId: number): Issue[] {
  return MOCK_ISSUES.filter((m) => m.opened_in <= snapshotId).map((m) => {
    const closed = m.closed_in !== undefined && m.closed_in <= snapshotId;
    return {
      id: m.id,
      snapshot_id: closed ? m.closed_in! - 1 : snapshotId,
      rule_id: m.rule_id,
      severity: m.severity,
      element_guid: m.element_guid,
      related_guid: m.related_guid ?? null,
      message: m.message,
      status: closed ? m.closed_as! : "open",
      discipline: disciplineOf(m.element_guid),
      first_seen_at: T(m.opened_in, 0),
      resolved_at: closed ? m.resolved_at ?? null : null,
      fixed_by: closed && m.closed_as === "fixed" ? m.fixed_by ?? null : null,
    };
  });
}

// ---------------------------------------------------------------- feedback
const FEEDBACK: Feedback[] = [
  { id: 1, element_guid: guid(4), rule_id: "R02", issue_id: 104, reason: "no_encuentro_codigo", comment: "No sé si un tabique de ladrillo es Ss_25_10_50 o Ss_25_10_30.", author: "Modelador ARQ", created_at: T(1, 35) },
  { id: 2, element_guid: guid(5), rule_id: "R02", issue_id: 105, reason: "no_encuentro_codigo", comment: null, author: "Modelador ARQ", created_at: T(1, 42) },
  { id: 3, element_guid: guid(8), rule_id: "R03", issue_id: 108, reason: "no_entiendo_regla", comment: "El código existe en otra tabla Uniclass.", author: "Modelador ARQ", created_at: T(1, 50) },
  { id: 4, element_guid: guid(12), rule_id: "R04", issue_id: 111, reason: "regla_no_aplica", comment: "La viga es de amarre; se une en obra.", author: "Modelador EST", created_at: T(1, 70) },
  { id: 5, element_guid: guid(15), rule_id: "R05", issue_id: 113, reason: "falta_informacion", comment: "Estructuras aún no define f'c de esta columna.", author: "Modelador EST", created_at: T(1, 95) },
  { id: 6, element_guid: guid(16), rule_id: "R05", issue_id: 114, reason: "falta_informacion", comment: null, author: "Modelador EST", created_at: T(2, 20) },
  { id: 7, element_guid: guid(9), rule_id: "R03", issue_id: 109, reason: "error_del_plugin", comment: "La ventana sí tiene el código correcto en el tipo.", author: "Modelador ARQ", created_at: T(2, -105) },
  { id: 8, element_guid: guid(1), rule_id: "R01", issue_id: 101, reason: "otro", comment: "Renombrado a MUR_LAD_e20.", author: "Modelador ARQ", created_at: T(2, -182) },
];

const feedbackUntil = (snapshotId: number) => {
  const limit = Date.parse(SNAPSHOT_DATES[snapshotId]) + 6 * 3600_000;
  return FEEDBACK.filter((f) => Date.parse(f.created_at) <= limit);
};

// ---------------------------------------------------------------- presupuesto
type Partida = { codigo: string; uniclass: string; descripcion: string; unidad: Unit; pu: number };
const PARTIDAS: Partida[] = [
  { codigo: "OE.2.3.3.1", uniclass: "Ss_20_05_15", descripcion: "Concreto f'c=210 kg/cm2 en zapatas", unidad: "m3", pu: 480 },
  { codigo: "OE.2.3.3.2", uniclass: "Ss_20_05_15", descripcion: "Acero fy=4200 kg/cm2 en zapatas", unidad: "kg", pu: 5.2 },
  { codigo: "OE.2.2.2.1", uniclass: "Ss_20_05_65", descripcion: "Concreto ciclópeo 1:10+30% PG en cimiento corrido", unidad: "m3", pu: 290 },
  { codigo: "OE.2.3.6.1", uniclass: "Ss_20_10_10", descripcion: "Concreto f'c=210 kg/cm2 en columnas", unidad: "m3", pu: 520 },
  { codigo: "OE.2.3.6.2", uniclass: "Ss_20_10_10", descripcion: "Encofrado y desencofrado en columnas", unidad: "m2", pu: 58 },
  { codigo: "OE.2.3.6.3", uniclass: "Ss_20_10_10", descripcion: "Acero fy=4200 kg/cm2 en columnas", unidad: "kg", pu: 5.2 },
  { codigo: "OE.2.3.7.1", uniclass: "Ss_20_10_20", descripcion: "Concreto f'c=210 kg/cm2 en vigas", unidad: "m3", pu: 510 },
  { codigo: "OE.2.3.7.2", uniclass: "Ss_20_10_20", descripcion: "Encofrado y desencofrado en vigas", unidad: "m2", pu: 62 },
  { codigo: "OE.2.3.7.3", uniclass: "Ss_20_10_20", descripcion: "Acero fy=4200 kg/cm2 en vigas", unidad: "kg", pu: 5.2 },
  { codigo: "OE.2.5.1.1", uniclass: "Ss_20_10_75", descripcion: "Estructura metálica de acero A36", unidad: "kg", pu: 9.5 },
  { codigo: "OE.2.3.5.1", uniclass: "Ss_25_10_20", descripcion: "Concreto f'c=210 kg/cm2 en placas", unidad: "m3", pu: 500 },
  { codigo: "OE.2.3.5.2", uniclass: "Ss_25_10_20", descripcion: "Encofrado y desencofrado en placas", unidad: "m2", pu: 55 },
  { codigo: "OE.3.1.1.1", uniclass: "Ss_25_10_50", descripcion: "Muro de ladrillo King Kong de soga", unidad: "m2", pu: 85 },
  { codigo: "OE.3.1.3.1", uniclass: "Ss_25_10_30", descripcion: "Tabique de drywall e=15 cm", unidad: "m2", pu: 95 },
  { codigo: "OE.2.3.8.1", uniclass: "Ss_30_10_30", descripcion: "Concreto f'c=210 kg/cm2 en losa maciza", unidad: "m3", pu: 495 },
  { codigo: "OE.2.3.9.1", uniclass: "Ss_30_10_35", descripcion: "Losa aligerada h=20 cm (concreto + ladrillo + acero)", unidad: "m2", pu: 165 },
  { codigo: "OE.3.9.1.1", uniclass: "Ss_25_30_20", descripcion: "Puerta contraplacada de madera", unidad: "und", pu: 650 },
  { codigo: "OE.3.10.1.1", uniclass: "Ss_25_30_95", descripcion: "Ventana de aluminio con vidrio simple", unidad: "m2", pu: 280 },
];

// cantidad y nº de elementos por partida en cada versión (ausente = no aparece)
const QUANTITIES: Record<number, Record<string, [number, number]>> = {
  1: {
    "OE.2.3.3.1": [18.4, 12], "OE.2.3.3.2": [920, 12], "OE.2.2.2.1": [12.75, 6],
    "OE.2.3.6.1": [9.6, 20], "OE.2.3.6.2": [96, 20], "OE.2.3.6.3": [1152, 20],
    "OE.2.3.7.1": [14.2, 14], "OE.2.3.7.2": [113.6, 14], "OE.2.3.7.3": [1562, 14],
    "OE.2.3.5.1": [6.3, 4], "OE.2.3.5.2": [50.4, 4],
    "OE.3.1.1.1": [412.5, 38], "OE.3.1.3.1": [86.4, 8],
    "OE.2.3.8.1": [7.2, 2], "OE.2.3.9.1": [245, 6],
    "OE.3.9.1.1": [14, 14], "OE.3.10.1.1": [32.4, 18],
  },
  2: {
    "OE.2.3.3.1": [18.4, 12], "OE.2.3.3.2": [920, 12], "OE.2.2.2.1": [12.75, 6],
    "OE.2.3.6.1": [10.8, 22], "OE.2.3.6.2": [108, 22], "OE.2.3.6.3": [1296, 22],
    "OE.2.3.7.1": [15.1, 16], "OE.2.3.7.2": [120.8, 16], "OE.2.3.7.3": [1661, 16],
    "OE.2.5.1.1": [1413, 2],
    "OE.2.3.5.1": [6.3, 4], "OE.2.3.5.2": [50.4, 4],
    "OE.3.1.1.1": [498.3, 46],
    "OE.2.3.8.1": [7.2, 2], "OE.2.3.9.1": [294, 7],
    "OE.3.9.1.1": [16, 16], "OE.3.10.1.1": [32.4, 18],
  },
};

const UNBUDGETED: Record<number, Budget["unbudgeted"]> = {
  1: { element_count: 10, guids_sample: [guid(2), guid(4), guid(5), guid(6), guid(7), guid(8), guid(9)], by_reason: { sin_codigo: 5, codigo_invalido: 2, sin_mapeo: 2, sin_cantidad: 1 } },
  2: { element_count: 3, guids_sample: [guid(9)], by_reason: { sin_mapeo: 2, sin_cantidad: 1 } },
};

function budgetLines(snapshotId: number): BudgetLine[] {
  const q = QUANTITIES[snapshotId] ?? {};
  return PARTIDAS.filter((p) => q[p.codigo]).map((p) => {
    const [cantidad, element_count] = q[p.codigo];
    return {
      partida_codigo: p.codigo,
      descripcion: p.descripcion,
      unidad: p.unidad,
      cantidad,
      precio_unitario: p.pu,
      subtotal: round2(cantidad * p.pu),
      element_count,
      uniclass_codes: [p.uniclass],
      pendiente_validar: true,
    };
  });
}

// ---------------------------------------------------------------- store
let snapshots: Snapshot[] = initialSnapshots();

export function resetMockStore(): void {
  snapshots = initialSnapshots();
}

const delay = <V>(value: V, ms = 120) => new Promise<V>((r) => setTimeout(() => r(structuredClone(value)), ms));

function resolveSnapshot(id?: number): Snapshot {
  const s = id === undefined ? snapshots[0] : snapshots.find((x) => x.id === id);
  if (!s) throw new ApiError(404, `No existe el snapshot ${id}`);
  return s;
}

function withCounts(s: Snapshot): Snapshot {
  return { ...s, open_issue_count: issuesAt(s.id).filter((i) => i.status === "open").length };
}

function computeStats(s: Snapshot): Stats {
  const issues = issuesAt(s.id);
  const open = issues.filter((i) => i.status === "open");
  const fb = feedbackUntil(s.id);
  const by_discipline = (["ARQ", "EST"] as const).map((d) => {
    const element_count = ELEMENT_COUNTS[s.id][d];
    const dOpen = open.filter((i) => i.discipline === d);
    const bad = new Set(dOpen.filter((i) => i.severity !== "info").map((i) => i.element_guid)).size;
    const conforming_count = element_count - bad;
    return {
      discipline: d,
      element_count,
      conforming_count,
      conformance_pct: round2((conforming_count / element_count) * 100),
      open_errors: dOpen.filter((i) => i.severity === "error").length,
      open_warnings: dOpen.filter((i) => i.severity === "warning").length,
    };
  });
  const element_count = by_discipline.reduce((a, d) => a + d.element_count, 0);
  const conforming = by_discipline.reduce((a, d) => a + d.conforming_count, 0);
  const by_rule: RuleStats[] = Object.entries(RULE_NAMES).map(([rule_id, rule_name]) => ({
    rule_id,
    rule_name,
    open_count: open.filter((i) => i.rule_id === rule_id).length,
    fixed_count: issues.filter((i) => i.rule_id === rule_id && i.status === "fixed").length,
    feedback_count: fb.filter((f) => f.rule_id === rule_id).length,
  }));
  const feedback_by_reason: Record<string, number> = {};
  for (const f of fb) feedback_by_reason[f.reason] = (feedback_by_reason[f.reason] ?? 0) + 1;
  const snapshots_by_cde_state: Record<string, number> = { WIP: 0, SHARED: 0, PUBLISHED: 0, ARCHIVED: 0 };
  for (const x of snapshots) snapshots_by_cde_state[x.cde_state] += 1;
  return {
    snapshot_id: s.id,
    cde_state: s.cde_state,
    element_count,
    conformance_pct: round2((conforming / element_count) * 100),
    can_move_to_shared: open.every((i) => i.severity !== "error"),
    by_discipline,
    by_rule,
    feedback_by_reason,
    snapshots_by_cde_state,
    fixed_one_click: issues.filter((i) => i.fixed_by === "one_click").length,
    fixed_manual: issues.filter((i) => i.fixed_by === "manual").length,
  };
}

function computeBudget(s: Snapshot): Budget {
  const lines = budgetLines(s.id);
  return {
    snapshot_id: s.id,
    cde_state: s.cde_state,
    is_official: s.cde_state === "PUBLISHED",
    currency: "PEN",
    total: round2(lines.reduce((a, l) => a + l.subtotal, 0)),
    lines,
    unbudgeted: UNBUDGETED[s.id],
    overlap_warnings: issuesAt(s.id).filter((i) => i.rule_id === "R04" && i.status === "open").length,
  };
}

function computeDiff(fromId: number, toId: number): BudgetDiff {
  const a = computeBudget(resolveSnapshot(fromId));
  const b = computeBudget(resolveSnapshot(toId));
  const lines: BudgetDiffLine[] = PARTIDAS.flatMap((p) => {
    const la = a.lines.find((l) => l.partida_codigo === p.codigo);
    const lb = b.lines.find((l) => l.partida_codigo === p.codigo);
    if (!la && !lb) return [];
    const subtotal_from = la?.subtotal ?? 0;
    const subtotal_to = lb?.subtotal ?? 0;
    const change: BudgetDiffLine["change"] = !la ? "added" : !lb ? "removed" : la.cantidad !== lb.cantidad ? "changed" : "unchanged";
    return [{
      partida_codigo: p.codigo,
      descripcion: p.descripcion,
      unidad: p.unidad,
      cantidad_from: la?.cantidad ?? 0,
      cantidad_to: lb?.cantidad ?? 0,
      subtotal_from,
      subtotal_to,
      delta_subtotal: round2(subtotal_to - subtotal_from),
      change,
    }];
  });
  const delta_total = round2(b.total - a.total);
  const forward = fromId < toId;
  return {
    from_snapshot_id: fromId,
    to_snapshot_id: toId,
    total_from: a.total,
    total_to: b.total,
    delta_total,
    delta_pct: a.total === 0 ? null : round2((delta_total / a.total) * 100),
    lines,
    elements_added: fromId === toId ? 0 : forward ? 11 : 2,
    elements_removed: fromId === toId ? 0 : forward ? 2 : 11,
    elements_modified: fromId === toId ? 0 : 7,
  };
}

function computeRecommendations(s: Snapshot): Recommendation[] {
  const stats = computeStats(s);
  const budget = computeBudget(s);
  const rule = (id: string) => stats.by_rule.find((r) => r.rule_id === id)!;
  const est = stats.by_discipline.find((d) => d.discipline === "EST")!;
  const r04Open = rule("R04").open_count;
  const errors = stats.by_discipline.reduce((a, d) => a + d.open_errors, 0);
  const recs: Recommendation[] = [];
  if (errors > 0) {
    recs.push({
      id: `rec-${s.id}-errores`,
      title: "Corregir errores antes de compartir",
      text: `Hay ${errors} issues de severidad error abiertos; mientras no sean 0 el modelo no puede pasar a SHARED. ${rule("R02").open_count} son elementos sin código Uniclass, que hoy quedan fuera del presupuesto.`,
      priority: "alta",
      facts: { errores_abiertos: errors, r02_abiertos: rule("R02").open_count },
      mode: "mock",
    });
  }
  if (r04Open > 0) {
    recs.push({
      id: `rec-${s.id}-r04`,
      title: "Unir geometría muro–viga",
      text: `Quedan ${r04Open} superposiciones muro–viga sin unir. El concreto de esas zonas se cuenta dos veces: corregirlas con "Unir geometría" evita inflar el metrado.`,
      priority: errors > 0 ? "media" : "alta",
      facts: { r04_abiertos: r04Open, r04_corregidos: rule("R04").fixed_count },
      mode: "mock",
    });
  }
  recs.push({
    id: `rec-${s.id}-loin`,
    title: "Completar el LOIN de Estructuras",
    text: `Estructuras tiene ${est.open_warnings} advertencias abiertas y ${est.conformance_pct}% de conformidad. La causa más reportada en la microencuesta es "falta información" (${stats.feedback_by_reason["falta_informacion"] ?? 0} respuestas): conviene definir f'c y material con el especialista.`,
    priority: "media",
    facts: { est_advertencias_abiertas: est.open_warnings, est_conformidad_pct: est.conformance_pct, feedback_falta_informacion: stats.feedback_by_reason["falta_informacion"] ?? 0 },
    mode: "mock",
  });
  recs.push({
    id: `rec-${s.id}-clasif`,
    title: "Reforzar la guía de clasificación Uniclass",
    text: `${stats.feedback_by_reason["no_encuentro_codigo"] ?? 0} modeladores respondieron "no encuentro el código". La corrección en un clic resolvió ${stats.fixed_one_click} issues frente a ${stats.fixed_manual} manuales: difundir la sugerencia automática ahorra tiempo.`,
    priority: "media",
    facts: { feedback_no_encuentro_codigo: stats.feedback_by_reason["no_encuentro_codigo"] ?? 0, corregidos_un_clic: stats.fixed_one_click, corregidos_manual: stats.fixed_manual },
    mode: "mock",
  });
  recs.push({
    id: `rec-${s.id}-precios`,
    title: "Validar precios unitarios con Costos",
    text: `Las ${budget.lines.filter((l) => l.pendiente_validar).length} partidas del presupuesto usan precios de ejemplo marcados PENDIENTE VALIDAR. El total estimado de ${formatPEN(budget.total)} solo será oficial cuando el modelo esté en PUBLISHED.`,
    priority: "baja",
    facts: { partidas_pendiente_validar: budget.lines.filter((l) => l.pendiente_validar).length, total_estimado_pen: budget.total, elementos_no_presupuestados: budget.unbudgeted.element_count },
    mode: "mock",
  });
  return recs;
}

function buildThread(g: string): ElementThread {
  const latestSnap = snapshots[0].id;
  const all = issuesAt(latestSnap).filter((i) => i.element_guid === g);
  const fb = FEEDBACK.filter((f) => f.element_guid === g);
  if (all.length === 0 && fb.length === 0 && !ELEMENT_BY_GUID.has(g)) {
    throw new ApiError(404, `No existe el elemento ${g}`);
  }
  const events: ThreadEvent[] = [];
  for (const issue of all) {
    const m = MOCK_ISSUES.find((x) => x.id === issue.id)!;
    events.push({ at: issue.first_seen_at, kind: "issue_opened", snapshot_id: m.opened_in, issue });
    if (issue.status !== "open" && issue.resolved_at) {
      events.push({
        at: issue.resolved_at,
        kind: issue.status === "fixed" ? "issue_fixed" : "issue_dismissed",
        snapshot_id: m.closed_in ?? null,
        issue,
      });
    }
  }
  for (const f of fb) events.push({ at: f.created_at, kind: "feedback", snapshot_id: null, feedback: f });
  events.sort((a, b) => a.at.localeCompare(b.at));
  return { guid: g, latest: ELEMENT_BY_GUID.get(g), events };
}

// ---------------------------------------------------------------- cliente mock
export const mockApi: ApiClient = {
  source: "mock",
  health: () => delay({ status: "ok" as const, version: "mock", llm_mode: "mock" as const }),
  listSnapshots: () => delay(snapshots.map(withCounts)),
  async setCdeState(snapshotId: number, cdeState: CdeState) {
    await delay(null);
    const s = resolveSnapshot(snapshotId);
    if (cdeState === "SHARED") {
      const errors = issuesAt(s.id).filter((i) => i.status === "open" && i.severity === "error").length;
      if (errors > 0) {
        throw new ApiError(409, `No se puede pasar a SHARED: el snapshot tiene ${errors} issues de severidad error abiertos.`);
      }
    }
    s.cde_state = cdeState;
    return withCounts(s);
  },
  listIssues: (filters: IssueFilters = {}) =>
    wrap(() =>
      issuesAt(resolveSnapshot(filters.snapshot_id).id).filter(
        (i) =>
          (!filters.status || i.status === filters.status) &&
          (!filters.discipline || i.discipline === filters.discipline) &&
          (!filters.rule_id || i.rule_id === filters.rule_id),
      ),
    ),
  getElementThread: (g: string) => wrap(() => buildThread(g)),
  listFeedback: () => delay(FEEDBACK),
  getStats: (id?: number) => wrap(() => computeStats(resolveSnapshot(id))),
  getBudget: (id?: number) => wrap(() => computeBudget(resolveSnapshot(id))),
  getBudgetDiff: (fromId: number, toId: number) => wrap(() => computeDiff(fromId, toId)),
  getRecommendations: (id?: number) => wrap(() => computeRecommendations(resolveSnapshot(id))),
  exportUrl: () => null,
};

function wrap<V>(fn: () => V): Promise<V> {
  try {
    return delay(fn());
  } catch (e) {
    return Promise.reject(e);
  }
}
