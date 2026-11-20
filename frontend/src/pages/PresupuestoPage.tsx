import { useEffect, useState } from "react";
import type { BudgetDiffLine, Snapshot } from "../api/types";
import { Card, ErrorBox, HBars, Loading, Pill, Stat } from "../components/ui";
import { formatInt, formatPEN, formatQty, formatSignedPEN, formatSignedPct } from "../format";
import { UNBUDGETED_REASON_LABELS } from "../rules";
import { useApi, useApp } from "../state";

const snapLabel = (s: Snapshot) => `${s.version_label} · ${s.cde_state}`;

export default function PresupuestoPage() {
  const { snapshots, selectedId, setSelectedId } = useApp();
  const [view, setView] = useState<"presupuesto" | "diff">("presupuesto");
  return (
    <div>
      <div className="page-head">
        <h1>Presupuesto 5D</h1>
        <div className="segmented" role="tablist">
          <button role="tab" aria-selected={view === "presupuesto"} className={view === "presupuesto" ? "on" : ""} onClick={() => setView("presupuesto")}>
            Presupuesto
          </button>
          <button role="tab" aria-selected={view === "diff"} className={view === "diff" ? "on" : ""} onClick={() => setView("diff")} disabled={snapshots.length < 2} title={snapshots.length < 2 ? "Se necesitan dos versiones" : undefined}>
            Comparar versiones
          </button>
        </div>
        {view === "presupuesto" && (
          <label className="inline-select">
            Versión
            <select value={selectedId} onChange={(e) => setSelectedId(Number(e.target.value))}>
              {snapshots.map((s) => (
                <option key={s.id} value={s.id}>
                  {snapLabel(s)}
                </option>
              ))}
            </select>
          </label>
        )}
      </div>
      {view === "presupuesto" ? <BudgetView /> : <DiffView />}
    </div>
  );
}

function BudgetView() {
  const { selectedId } = useApp();
  const budget = useApi((c) => c.getBudget(selectedId), [selectedId]);
  if (budget.error) return <ErrorBox error={budget.error} onRetry={budget.reload} />;
  if (!budget.data) return <Loading />;
  const b = budget.data;
  const pending = b.lines.filter((l) => l.pendiente_validar).length;
  const reasons = Object.entries(b.unbudgeted.by_reason).filter(([, n]) => n > 0);

  return (
    <div className="grid">
      <Card className="span-2 hero">
        <div className="hero-row">
          <div>
            <div className="hero-label">Total {b.is_official ? "oficial" : "estimado"} (sin IGV)</div>
            <div className="hero-number">{formatPEN(b.total)}</div>
          </div>
          <div className="hero-side">
            {b.is_official ? (
              <Pill tone="ok">Oficial (PUBLISHED)</Pill>
            ) : (
              <Pill tone="warn" title="Solo el presupuesto de una versión PUBLISHED es oficial (BEP §7)">
                Estimado · versión {b.cde_state}
              </Pill>
            )}
            <p className="small muted">
              {b.lines.length} partidas · moneda {b.currency}
              {pending > 0 && <> · {pending} con precio pendiente de validar</>}
            </p>
          </div>
        </div>
        {(b.overlap_warnings ?? 0) > 0 && (
          <div className="alert alert-warn">
            ⚠ {b.overlap_warnings} superposiciones muro–viga abiertas (R04): parte del volumen de concreto podría estar contado dos veces.
          </div>
        )}
      </Card>

      <Card title="No presupuestados">
        <Stat label="elementos fuera del presupuesto" value={formatInt(b.unbudgeted.element_count)} tone={b.unbudgeted.element_count ? "warn" : "ok"} />
        {reasons.length > 0 && (
          <HBars rows={reasons.map(([k, n]) => ({ key: k, label: UNBUDGETED_REASON_LABELS[k] ?? k, value: n, tone: "hbar-warn" }))} />
        )}
      </Card>

      <Card className="span-3" title="Partidas">
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Partida</th>
                <th>Descripción</th>
                <th>Unidad</th>
                <th className="num">Cantidad</th>
                <th className="num">P.U. (S/)</th>
                <th className="num">Subtotal</th>
              </tr>
            </thead>
            <tbody>
              {b.lines.map((l) => (
                <tr key={l.partida_codigo}>
                  <td className="mono">{l.partida_codigo}</td>
                  <td>
                    {l.descripcion}
                    {l.pendiente_validar && (
                      <span className="pv" title="Precio marcado PENDIENTE VALIDAR POR CONSTRUCCIÓN">
                        {" "}
                        <Pill tone="warn">pendiente validar</Pill>
                      </span>
                    )}
                    <div className="small muted">
                      {l.element_count} elementos · {l.uniclass_codes.join(", ")}
                    </div>
                  </td>
                  <td>{l.unidad}</td>
                  <td className="num">{formatQty(l.cantidad)}</td>
                  <td className="num">{formatQty(l.precio_unitario)}</td>
                  <td className="num strong">{formatPEN(l.subtotal)}</td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr>
                <td colSpan={5} className="num">
                  Total {b.is_official ? "oficial" : "estimado"}
                </td>
                <td className="num strong">{formatPEN(b.total)}</td>
              </tr>
            </tfoot>
          </table>
        </div>
      </Card>
    </div>
  );
}

const CHANGE_LABEL: Record<BudgetDiffLine["change"], string> = {
  added: "Nueva",
  removed: "Eliminada",
  changed: "Cambió",
  unchanged: "Sin cambio",
};
const CHANGE_TONE = { added: "info", removed: "bad", changed: "warn", unchanged: "neutral" } as const;

function DiffView() {
  const { snapshots, selectedId } = useApp();
  // snapshots: más reciente primero → por defecto comparar la seleccionada (o la penúltima) contra la última
  const sel = snapshots.findIndex((s) => s.id === selectedId);
  const [toId, setToId] = useState<number | undefined>(snapshots[0]?.id);
  const [fromId, setFromId] = useState<number | undefined>(snapshots[sel > 0 ? sel : 1]?.id);
  const [hideUnchanged, setHideUnchanged] = useState(false);
  useEffect(() => {
    if (fromId === toId && snapshots.length > 1) setFromId(snapshots.find((s) => s.id !== toId)?.id);
  }, [fromId, toId, snapshots]);

  const diff = useApi((c) => c.getBudgetDiff(fromId!, toId!), [fromId, toId]);
  const d = diff.data;
  const tone = (n: number) => (n > 0 ? "text-up" : n < 0 ? "text-down" : "");

  return (
    <div className="grid">
      <Card className="span-3">
        <div className="diff-pick">
          <label>
            Desde
            <select value={fromId} onChange={(e) => setFromId(Number(e.target.value))}>
              {snapshots.map((s) => (
                <option key={s.id} value={s.id}>
                  {snapLabel(s)}
                </option>
              ))}
            </select>
          </label>
          <span aria-hidden="true" className="arrow">→</span>
          <label>
            Hasta
            <select value={toId} onChange={(e) => setToId(Number(e.target.value))}>
              {snapshots.map((s) => (
                <option key={s.id} value={s.id}>
                  {snapLabel(s)}
                </option>
              ))}
            </select>
          </label>
        </div>
      </Card>
      {diff.error ? (
        <div className="span-3"><ErrorBox error={diff.error} onRetry={diff.reload} /></div>
      ) : !d ? (
        <div className="span-3"><Loading /></div>
      ) : (
        <>
          <Card className="span-2 hero" title="Variación del total">
            <div className="hero-row">
              <div className={`hero-number ${tone(d.delta_total)}`}>{formatSignedPEN(d.delta_total)}</div>
              <div className="hero-side">
                <div className={`big-pct ${tone(d.delta_total)}`}>{formatSignedPct(d.delta_pct)}</div>
                <p className="small muted">
                  {formatPEN(d.total_from)} → <strong>{formatPEN(d.total_to)}</strong>
                </p>
              </div>
            </div>
          </Card>
          <Card title="Elementos">
            <div className="stat-row stat-row-3">
              <Stat label="agregados" value={d.elements_added} tone="ok" />
              <Stat label="eliminados" value={d.elements_removed} tone="bad" />
              <Stat label="modificados" value={d.elements_modified} tone="warn" />
            </div>
          </Card>
          <Card
            className="span-3"
            title="Cambios por partida"
            actions={
              <label className="check">
                <input type="checkbox" checked={hideUnchanged} onChange={(e) => setHideUnchanged(e.target.checked)} /> Ocultar sin cambio
              </label>
            }
          >
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Cambio</th>
                    <th>Partida</th>
                    <th>Descripción</th>
                    <th className="num">Cantidad</th>
                    <th className="num">Subtotal desde</th>
                    <th className="num">Subtotal hasta</th>
                    <th className="num">Δ Subtotal</th>
                  </tr>
                </thead>
                <tbody>
                  {d.lines
                    .filter((l) => !hideUnchanged || l.change !== "unchanged")
                    .map((l) => (
                      <tr key={l.partida_codigo} className={`chg-${l.change}`}>
                        <td>
                          <Pill tone={CHANGE_TONE[l.change]}>{CHANGE_LABEL[l.change]}</Pill>
                        </td>
                        <td className="mono">{l.partida_codigo}</td>
                        <td>{l.descripcion}</td>
                        <td className="num">
                          {formatQty(l.cantidad_from)} → {formatQty(l.cantidad_to)} {l.unidad}
                        </td>
                        <td className="num">{formatPEN(l.subtotal_from)}</td>
                        <td className="num">{formatPEN(l.subtotal_to)}</td>
                        <td className={`num strong ${tone(l.delta_subtotal)}`}>{formatSignedPEN(l.delta_subtotal)}</td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
