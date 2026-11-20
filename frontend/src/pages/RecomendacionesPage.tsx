import type { Recommendation } from "../api/types";
import { Card, ErrorBox, Expander, Loading, Pill } from "../components/ui";
import { formatQty } from "../format";
import { useApi, useApp } from "../state";

const PRIORITY_TONE = { alta: "bad", media: "warn", baja: "info" } as const;
const PRIORITY_ORDER = { alta: 0, media: 1, baja: 2 } as const;
const MODE_LABEL: Record<Recommendation["mode"], string> = {
  mock: "IA simulada (mock)",
  openrouter: "IA · OpenRouter",
  anthropic: "IA · Anthropic",
  ollama: "IA · Ollama (local)",
};

export default function RecomendacionesPage() {
  const { selectedId, health } = useApp();
  const recs = useApi((c) => c.getRecommendations(selectedId), [selectedId]);

  if (recs.error) return <ErrorBox error={recs.error} onRetry={recs.reload} />;
  if (!recs.data) return <Loading label="Generando recomendaciones…" />;
  const list = [...recs.data].sort((a, b) => PRIORITY_ORDER[a.priority] - PRIORITY_ORDER[b.priority]);
  const mode = list[0]?.mode ?? health.llm_mode;

  return (
    <div>
      <div className="page-head">
        <h1>Recomendaciones para el PM</h1>
        <Pill tone={mode === "mock" ? "neutral" : "info"}>Modo: {MODE_LABEL[mode] ?? mode}</Pill>
      </div>
      <p className="muted lead">
        Cada cifra del texto proviene de <code>facts</code>, calculados por SQL en el backend. La IA redacta; no inventa números.
      </p>
      {list.length === 0 ? (
        <p className="empty">Sin recomendaciones para esta versión.</p>
      ) : (
        <div className="rec-grid">
          {list.map((r) => (
            <Card key={r.id} className={`rec rec-${r.priority}`}>
              <div className="rec-head">
                <Pill tone={PRIORITY_TONE[r.priority]}>Prioridad {r.priority}</Pill>
              </div>
              <h3>{r.title}</h3>
              <p>{r.text}</p>
              <Expander label="Ver datos">
                <table className="table facts">
                  <thead>
                    <tr>
                      <th>Dato</th>
                      <th className="num">Valor</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(r.facts).map(([k, v]) => (
                      <tr key={k}>
                        <td className="mono">{k}</td>
                        <td className="num mono">{typeof v === "number" ? (Number.isInteger(v) ? v : formatQty(v)) : v}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Expander>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
