// Nombres y etiquetas en español. Nombres de regla copiados de data/rules.json (v0.1.0);
// cuando hay backend, la UI prefiere el rule_name que llega en /stats.
import type { CdeState, FeedbackReason } from "./api/types";

export const RULE_NAMES: Record<string, string> = {
  R01: "Nombre de tipo genérico",
  R02: "Elemento sin código Uniclass",
  R03: "Código Uniclass inexistente o de otra categoría",
  R04: "Superposición muro–viga",
  R05: "Parámetro LOIN faltante",
  R06: "Nombre de archivo fuera de ISO 19650",
  R07: "Elemento sin nivel",
};

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
