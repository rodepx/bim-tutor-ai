import { useId, useState, type ReactNode } from "react";
import { ApiError, type CdeState } from "../api/types";
import { CDE_LABELS } from "../rules";

export function Card({ title, children, actions, className = "" }: { title?: ReactNode; children: ReactNode; actions?: ReactNode; className?: string }) {
  return (
    <section className={`card ${className}`}>
      {(title || actions) && (
        <header className="card-head">
          {title && <h2>{title}</h2>}
          {actions}
        </header>
      )}
      {children}
    </section>
  );
}

export function Stat({ label, value, tone, hint }: { label: string; value: ReactNode; tone?: "ok" | "warn" | "bad" | "neutral"; hint?: ReactNode }) {
  return (
    <div className={`stat tone-${tone ?? "neutral"}`}>
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
      {hint && <div className="stat-hint">{hint}</div>}
    </div>
  );
}

export function Pill({ tone, children, title }: { tone: "ok" | "warn" | "bad" | "info" | "neutral"; children: ReactNode; title?: string }) {
  return (
    <span className={`pill pill-${tone}`} title={title}>
      {children}
    </span>
  );
}

const CDE_TONE: Record<CdeState, "warn" | "info" | "ok" | "neutral"> = {
  WIP: "warn",
  SHARED: "info",
  PUBLISHED: "ok",
  ARCHIVED: "neutral",
};

export function CdeBadge({ state }: { state: CdeState }) {
  return <Pill tone={CDE_TONE[state]}>{CDE_LABELS[state]}</Pill>;
}

export function Loading({ label = "Cargando…" }: { label?: string }) {
  return (
    <div className="loading" role="status">
      <span className="spinner" aria-hidden="true" /> {label}
    </div>
  );
}

export function errorMessage(e: unknown): string {
  if (e instanceof ApiError) return `${e.detail} (HTTP ${e.status})`;
  if (e instanceof Error) return e.message;
  return String(e);
}

export function ErrorBox({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  return (
    <div className="alert alert-bad" role="alert">
      <strong>No se pudo cargar.</strong> {errorMessage(error)}
      {onRetry && (
        <button className="btn btn-small" onClick={onRetry}>
          Reintentar
        </button>
      )}
    </div>
  );
}

/** Barras horizontales simples (sin librería de gráficos). */
export function HBars({ rows, max }: { rows: { key: string; label: ReactNode; value: number; secondary?: number; tone?: string }[]; max?: number }) {
  const top = max ?? Math.max(1, ...rows.map((r) => r.value + (r.secondary ?? 0)));
  return (
    <ul className="hbars">
      {rows.map((r) => (
        <li key={r.key}>
          <div className="hbar-label">{r.label}</div>
          <div className="hbar-track" aria-hidden="true">
            <div className={`hbar-fill ${r.tone ?? ""}`} style={{ width: `${(r.value / top) * 100}%` }} />
            {r.secondary ? <div className="hbar-fill hbar-secondary" style={{ width: `${(r.secondary / top) * 100}%` }} /> : null}
          </div>
          <div className="hbar-value">
            {r.value}
            {r.secondary !== undefined && <span className="hbar-sec" title="corregidos"> · {r.secondary}✓</span>}
          </div>
        </li>
      ))}
    </ul>
  );
}

export function Expander({ label, children }: { label: string; children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  return (
    <div className="expander">
      <button className="btn btn-link" aria-expanded={open} aria-controls={id} onClick={() => setOpen((o) => !o)}>
        {open ? "▾" : "▸"} {label}
      </button>
      {open && <div id={id}>{children}</div>}
    </div>
  );
}

export function Meter({ pct, tone }: { pct: number; tone: "ok" | "warn" | "bad" }) {
  return (
    <div className="meter" role="meter" aria-valuemin={0} aria-valuemax={100} aria-valuenow={pct}>
      <div className={`meter-fill tone-bg-${tone}`} style={{ width: `${Math.min(100, Math.max(0, pct))}%` }} />
    </div>
  );
}
