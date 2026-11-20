import { useEffect, useState } from "react";
import type { Discipline, Issue, IssueStatus, ThreadEvent } from "../api/types";
import { ErrorBox, Loading, Pill } from "../components/ui";
import { formatDate, shortGuid } from "../format";
import { DISCIPLINE_LABELS, RULE_NAMES, SEVERITY_LABELS, STATUS_LABELS, feedbackReasonLabel } from "../rules";
import { useApi, useApp } from "../state";

const STATUS_TONE = { open: "bad", fixed: "ok", dismissed: "neutral" } as const;
const SEV_TONE = { error: "bad", warning: "warn", info: "info" } as const;

export default function IssuesPage() {
  const { selectedId } = useApp();
  const [status, setStatus] = useState<IssueStatus | "">("open");
  const [discipline, setDiscipline] = useState<Discipline | "">("");
  const [ruleId, setRuleId] = useState("");
  const [guid, setGuid] = useState<string>();

  const issues = useApi(
    (c) =>
      c.listIssues({
        snapshot_id: selectedId,
        status: status || undefined,
        discipline: discipline || undefined,
        rule_id: ruleId || undefined,
      }),
    [selectedId, status, discipline, ruleId],
  );

  const rows = issues.data ?? [];

  return (
    <div className={guid ? "split" : ""}>
      <section className="card">
        <header className="card-head">
          <h2>Issues {issues.data && <span className="muted">({rows.length})</span>}</h2>
          <div className="filters">
            <label>
              Estado
              <select value={status} onChange={(e) => setStatus(e.target.value as IssueStatus | "")}>
                <option value="">Todos</option>
                <option value="open">Abiertos</option>
                <option value="fixed">Corregidos</option>
                <option value="dismissed">Descartados</option>
              </select>
            </label>
            <label>
              Disciplina
              <select value={discipline} onChange={(e) => setDiscipline(e.target.value as Discipline | "")}>
                <option value="">Todas</option>
                <option value="ARQ">ARQ · Arquitectura</option>
                <option value="EST">EST · Estructuras</option>
                <option value="MEP">MEP · Instalaciones</option>
              </select>
            </label>
            <label>
              Regla
              <select value={ruleId} onChange={(e) => setRuleId(e.target.value)}>
                <option value="">Todas</option>
                {Object.entries(RULE_NAMES).map(([id, name]) => (
                  <option key={id} value={id}>
                    {id} · {name}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </header>
        {issues.error ? (
          <ErrorBox error={issues.error} onRetry={issues.reload} />
        ) : issues.loading && !issues.data ? (
          <Loading />
        ) : rows.length === 0 ? (
          <p className="empty">No hay issues con estos filtros. ✔</p>
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Regla</th>
                  <th>Severidad</th>
                  <th>Estado</th>
                  <th>Disc.</th>
                  <th>Mensaje</th>
                  <th>Elemento</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((i) => (
                  <IssueRow key={i.id} issue={i} active={guid === i.element_guid} onOpen={setGuid} />
                ))}
              </tbody>
            </table>
          </div>
        )}
        <p className="small muted">Haz clic en una fila para ver el historial del elemento entre versiones.</p>
      </section>
      {guid && <ThreadPanel guid={guid} onClose={() => setGuid(undefined)} />}
    </div>
  );
}

function IssueRow({ issue: i, active, onOpen }: { issue: Issue; active: boolean; onOpen: (g: string) => void }) {
  const g = i.element_guid;
  const open = () => g && onOpen(g);
  return (
    <tr
      className={`${g ? "clickable" : ""} ${active ? "row-active" : ""}`}
      onClick={open}
      onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && (e.preventDefault(), open())}
      tabIndex={g ? 0 : -1}
      title={g ? "Ver historial del elemento" : "Regla de documento: sin elemento"}
    >
      <td>
        <strong>{i.rule_id}</strong>
        <div className="small muted">{RULE_NAMES[i.rule_id] ?? ""}</div>
      </td>
      <td>
        <Pill tone={SEV_TONE[i.severity]}>{SEVERITY_LABELS[i.severity]}</Pill>
      </td>
      <td>
        <Pill tone={STATUS_TONE[i.status]}>{STATUS_LABELS[i.status]}</Pill>
        {i.fixed_by && <div className="small muted">{i.fixed_by === "one_click" ? "en 1 clic" : "manual"}</div>}
      </td>
      <td>{i.discipline ?? "—"}</td>
      <td className="msg">{i.message}</td>
      <td className="mono">{g ? shortGuid(g) : <span className="muted">Documento</span>}</td>
    </tr>
  );
}

const EVENT_TEXT: Record<ThreadEvent["kind"], string> = {
  issue_opened: "Issue detectado",
  issue_fixed: "Issue corregido",
  issue_dismissed: "Issue descartado",
  feedback: "Microencuesta: «No pude, ¿por qué?»",
};
const EVENT_TONE: Record<ThreadEvent["kind"], string> = {
  issue_opened: "bad",
  issue_fixed: "ok",
  issue_dismissed: "neutral",
  feedback: "info",
};

function ThreadPanel({ guid, onClose }: { guid: string; onClose: () => void }) {
  const thread = useApi((c) => c.getElementThread(guid), [guid]);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  const el = thread.data?.latest;
  return (
    <aside className="card thread" aria-label="Historial del elemento">
      <header className="card-head">
        <h2>Historial del elemento</h2>
        <button className="btn btn-small" onClick={onClose} aria-label="Cerrar historial">
          Cerrar ✕
        </button>
      </header>
      <div className="mono small break">{guid}</div>
      {thread.error ? (
        <ErrorBox error={thread.error} onRetry={thread.reload} />
      ) : !thread.data ? (
        <Loading />
      ) : (
        <>
          {el && (
            <dl className="element-facts">
              <dt>Tipo</dt>
              <dd className="mono">{el.type_name}</dd>
              <dt>Categoría</dt>
              <dd>
                {el.category} · {el.discipline} ({DISCIPLINE_LABELS[el.discipline]})
              </dd>
              <dt>Nivel</dt>
              <dd>{el.level ?? <span className="text-warn">sin nivel</span>}</dd>
              <dt>Uniclass</dt>
              <dd className="mono">{el.classification_code ?? <span className="text-bad">sin código</span>}</dd>
            </dl>
          )}
          <ol className="timeline">
            {thread.data.events.map((ev, idx) => (
              <li key={idx} className={`tl-item tl-${EVENT_TONE[ev.kind]}`}>
                <div className="tl-dot" aria-hidden="true" />
                <div className="tl-body">
                  <div className="tl-head">
                    <strong>{EVENT_TEXT[ev.kind]}</strong>
                    <span className="small muted">
                      {formatDate(ev.at)}
                      {ev.snapshot_id != null ? ` · snapshot #${ev.snapshot_id}` : ""}
                    </span>
                  </div>
                  {ev.issue && (
                    <div className="small">
                      <strong>{ev.issue.rule_id}</strong> {RULE_NAMES[ev.issue.rule_id] ?? ""} — {ev.issue.message}
                      {ev.kind === "issue_fixed" && ev.issue.fixed_by && (
                        <> · {ev.issue.fixed_by === "one_click" ? "corregido en 1 clic" : "corregido manualmente"}</>
                      )}
                    </div>
                  )}
                  {ev.feedback && (
                    <div className="small">
                      <Pill tone="info">{feedbackReasonLabel(ev.feedback.reason)}</Pill> regla {ev.feedback.rule_id}
                      {ev.feedback.comment && <blockquote>“{ev.feedback.comment}”</blockquote>}
                      {ev.feedback.author && <div className="muted">— {ev.feedback.author}</div>}
                    </div>
                  )}
                </div>
              </li>
            ))}
          </ol>
          {thread.data.events.length === 0 && <p className="muted">Sin eventos registrados.</p>}
        </>
      )}
    </aside>
  );
}
