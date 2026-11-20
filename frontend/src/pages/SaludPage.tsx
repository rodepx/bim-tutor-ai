import { useEffect, useState } from "react";
import type { CdeState } from "../api/types";
import { Card, CdeBadge, ErrorBox, HBars, Loading, Meter, Pill, Stat, errorMessage } from "../components/ui";
import { conformanceTone, formatInt, formatPct } from "../format";
import { CDE_LABELS, CDE_ORDER, DISCIPLINE_LABELS, RULE_NAMES, feedbackReasonLabel, openBySeverity } from "../rules";
import { useApi, useApp } from "../state";

const NEXT_STATE: Partial<Record<CdeState, CdeState>> = { WIP: "SHARED", SHARED: "PUBLISHED", PUBLISHED: "ARCHIVED" };

export default function SaludPage() {
  const { selectedId } = useApp();
  const stats = useApi((c) => c.getStats(selectedId), [selectedId]);

  if (stats.loading && !stats.data) return <Loading />;
  if (stats.error) return <ErrorBox error={stats.error} onRetry={stats.reload} />;
  const s = stats.data!;
  const { errors: openErrors, warnings: openWarnings } = openBySeverity(s.by_rule);
  const totalFixed = s.fixed_one_click + s.fixed_manual;
  const tone = conformanceTone(s.conformance_pct);
  const feedback = Object.entries(s.feedback_by_reason).sort((a, b) => b[1] - a[1]);

  return (
    <div className="grid">
      <Card className="span-2 hero" title="Conformidad global">
        <div className="hero-row">
          <div className={`hero-number tone-${tone}`}>{formatPct(s.conformance_pct)}</div>
          <div className="hero-side">
            <p className="muted">
              de <strong>{formatInt(s.element_count)}</strong> elementos sin errores ni advertencias abiertas
            </p>
            <Meter pct={s.conformance_pct} tone={tone} />
          </div>
        </div>
        <div className="stat-row">
          <Stat label="Errores abiertos" value={openErrors} tone={openErrors > 0 ? "bad" : "ok"} />
          <Stat label="Advertencias abiertas" value={openWarnings} tone={openWarnings > 0 ? "warn" : "ok"} />
          <Stat label="Corregidos en 1 clic" value={s.fixed_one_click} tone="ok" hint={totalFixed ? `${formatPct((s.fixed_one_click / totalFixed) * 100)} del total` : undefined} />
          <Stat label="Corregidos manualmente" value={s.fixed_manual} />
        </div>
      </Card>

      <CdeCard state={s.cde_state} canShare={s.can_move_to_shared ?? openErrors === 0} openErrors={openErrors} byState={s.snapshots_by_cde_state} onMoved={stats.reload} />

      <Card title="Conformidad por disciplina">
        <div className="disc-list">
          {s.by_discipline.map((d) => {
            const t = conformanceTone(d.conformance_pct);
            return (
              <div key={d.discipline} className="disc">
                <div className="disc-head">
                  <span className="disc-name">
                    {d.discipline} <span className="muted">· {DISCIPLINE_LABELS[d.discipline]}</span>
                  </span>
                  <span className={`disc-pct tone-${t}`}>{formatPct(d.conformance_pct)}</span>
                </div>
                <Meter pct={d.conformance_pct} tone={t} />
                <div className="disc-meta">
                  {d.conforming_count}/{d.element_count} conformes ·{" "}
                  <span className={d.open_errors ? "text-bad" : ""}>{d.open_errors} errores</span> ·{" "}
                  <span className={d.open_warnings ? "text-warn" : ""}>{d.open_warnings} advertencias</span>
                </div>
              </div>
            );
          })}
        </div>
      </Card>

      <Card className="span-2" title="Issues por regla" actions={<span className="legend"><i className="lg-open" /> abiertos <i className="lg-fixed" /> corregidos</span>}>
        <HBars
          rows={s.by_rule.map((r) => ({
            key: r.rule_id,
            label: (
              <>
                <strong>{r.rule_id}</strong> {r.rule_name || RULE_NAMES[r.rule_id]}
              </>
            ),
            value: r.open_count,
            secondary: r.fixed_count,
            tone: "hbar-open",
          }))}
        />
      </Card>

      <Card title="¿Por qué no pudieron corregir?">
        {feedback.length === 0 ? (
          <p className="muted">Sin respuestas de la microencuesta.</p>
        ) : (
          <HBars rows={feedback.map(([k, v]) => ({ key: k, label: feedbackReasonLabel(k), value: v, tone: "hbar-fb" }))} />
        )}
      </Card>
    </div>
  );
}

function CdeCard({ state, canShare, openErrors, byState, onMoved }: { state: CdeState; canShare: boolean; openErrors: number; byState: Record<string, number>; onMoved: () => void }) {
  const { client, selectedId, refreshSnapshots } = useApp();
  const [target, setTarget] = useState<CdeState>(NEXT_STATE[state] ?? "WIP");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ tone: "ok" | "bad"; text: string }>();
  useEffect(() => setTarget(NEXT_STATE[state] ?? "WIP"), [state, selectedId]);
  useEffect(() => setMsg(undefined), [selectedId]);

  async function move() {
    if (selectedId === undefined) return;
    setBusy(true);
    setMsg(undefined);
    try {
      const snap = await client.setCdeState(selectedId, target);
      setMsg({ tone: "ok", text: `Versión ${snap.version_label} movida a ${snap.cde_state}.` });
      await refreshSnapshots();
      onMoved();
    } catch (e) {
      setMsg({ tone: "bad", text: errorMessage(e) });
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card title="Estado CDE">
      <div className="cde-now">
        <CdeBadge state={state} />
      </div>
      <div className={`gate ${canShare ? "gate-ok" : "gate-bad"}`}>
        <span className="gate-icon" aria-hidden="true">{canShare ? "✔" : "✖"}</span>
        <div>
          <strong>{canShare ? "Puede pasar a SHARED" : "No puede pasar a SHARED"}</strong>
          <div className="small">{canShare ? "0 errores abiertos" : `${openErrors} errores abiertos (se exige 0)`}</div>
        </div>
      </div>
      <div className="cde-move">
        <label>
          <span className="sr-only">Nuevo estado</span>
          <select value={target} onChange={(e) => setTarget(e.target.value as CdeState)}>
            {CDE_ORDER.filter((x) => x !== state).map((x) => (
              <option key={x} value={x}>
                {CDE_LABELS[x]}
              </option>
            ))}
          </select>
        </label>
        <button className="btn btn-primary" onClick={move} disabled={busy}>
          {busy ? "Moviendo…" : "Mover estado"}
        </button>
      </div>
      {msg && (
        <div className={`alert alert-${msg.tone}`} role="status">
          {msg.text}
        </div>
      )}
      <div className="cde-counts">
        {CDE_ORDER.map((x) => (
          <div key={x} className="cde-count">
            <div className="cde-count-n">{byState[x] ?? 0}</div>
            <Pill tone="neutral">{x}</Pill>
          </div>
        ))}
      </div>
      <p className="small muted">Versiones del proyecto por estado CDE (BEP §7).</p>
    </Card>
  );
}
