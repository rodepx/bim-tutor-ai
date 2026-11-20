// Formato es-PE para montos, cantidades y fechas.
const pen = new Intl.NumberFormat("es-PE", { style: "currency", currency: "PEN", minimumFractionDigits: 2, maximumFractionDigits: 2 });
const num2 = new Intl.NumberFormat("es-PE", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const num1 = new Intl.NumberFormat("es-PE", { minimumFractionDigits: 0, maximumFractionDigits: 1 });
const int = new Intl.NumberFormat("es-PE", { maximumFractionDigits: 0 });
const dateFmt = new Intl.DateTimeFormat("es-PE", { dateStyle: "medium", timeStyle: "short", timeZone: "America/Lima" });

/** "S/ 1,234.56" (formato es-PE, 2 decimales). */
export function formatPEN(n: number | null | undefined): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  return pen.format(n).replace(/ /g, " ");
}

/** Monto con signo explícito: "+S/ 10.00" / "−S/ 10.00". */
export function formatSignedPEN(n: number): string {
  if (n === 0) return formatPEN(0);
  return (n > 0 ? "+" : "−") + formatPEN(Math.abs(n));
}

export function formatQty(n: number | null | undefined): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  return num2.format(n);
}

export function formatInt(n: number): string {
  return int.format(n);
}

/** Porcentaje con 1 decimal máximo: "87.5 %". */
export function formatPct(n: number | null | undefined): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  return `${num1.format(n)} %`;
}

export function formatSignedPct(n: number | null | undefined): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  if (n === 0) return "0 %";
  return (n > 0 ? "+" : "−") + formatPct(Math.abs(n));
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : dateFmt.format(d).replace(/ /g, " ");
}

/** Verde/ámbar/rojo según % de conformidad. */
export function conformanceTone(pct: number): "ok" | "warn" | "bad" {
  if (pct >= 95) return "ok";
  if (pct >= 80) return "warn";
  return "bad";
}

export function shortGuid(guid: string): string {
  return guid.length > 14 ? `${guid.slice(0, 8)}…${guid.slice(-6)}` : guid;
}
