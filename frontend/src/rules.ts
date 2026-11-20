// Nombres y etiquetas en español. Nombre y severidad de cada regla se leen de data/rules.json
// (misma fuente que el plugin); cuando hay backend, la UI prefiere el rule_name que llega en /stats.
import type { CdeState, FeedbackReason, RuleStats, Severity } from "./api/types";
import rulesData from "../../data/rules.json";

const RULES: { id: string; name: string; severity: string }[] = rulesData.rules;

export const RULE_NAMES: Record<string, string> = Object.fromEntries(RULES.map((r) => [r.id, r.name]));

export const RULE_SEVERITY: Record<string, Severity> = Object.fromEntries(
  RULES.map((r) => [r.id, r.severity as Severity]),
);

/**
 * Errores y advertencias abiertos del snapshot a partir de by_rule (incluye reglas de documento
 * como R06, que no tienen disciplina y por eso no suman en by_discipline).
 */
export function openBySeverity(byRule: RuleStats[]): { errors: number; warnings: number } {
  let errors = 0;
  let warnings = 0;
  for (const r of byRule) {
    const sev = RULE_SEVERITY[r.rule_id];
    if (sev === "error") errors += r.open_count;
    else if (sev === "warning") warnings += r.open_count;
  }
  return { errors, warnings };
}

export const FEEDBACK_REASON_LABELS: Record<FeedbackReason, string> = {
  no_entiendo_regla: "No entiendo la regla",
  no_encuentro_codigo: "No encuentro el código",
  falta_informacion: "Falta información",
  regla_no_aplica: "La regla no aplica",
  error_del_plugin: "Error del plugin",
  otro: "Otro motivo",
};

export const UNBUDGETED_REASON_LABELS: Record<string, string> = {
  sin_codigo: "Sin código Uniclass",
  codigo_invalido: "Código inválido",
  sin_mapeo: "Código sin partida asignada",
  sin_cantidad: "Sin cantidad (magnitud nula)",
};

export const CDE_LABELS: Record<CdeState, string> = {
  WIP: "WIP · En curso",
  SHARED: "SHARED · Compartido",
  PUBLISHED: "PUBLISHED · Publicado",
  ARCHIVED: "ARCHIVED · Archivado",
};

export const CDE_ORDER: CdeState[] = ["WIP", "SHARED", "PUBLISHED", "ARCHIVED"];

export const STATUS_LABELS = { open: "Abierto", fixed: "Corregido", dismissed: "Descartado" } as const;
export const SEVERITY_LABELS = { error: "Error", warning: "Advertencia", info: "Info" } as const;
export const DISCIPLINE_LABELS = { ARQ: "Arquitectura", EST: "Estructuras", MEP: "Instalaciones" } as const;

export function feedbackReasonLabel(reason: string): string {
  return FEEDBACK_REASON_LABELS[reason as FeedbackReason] ?? reason;
}
