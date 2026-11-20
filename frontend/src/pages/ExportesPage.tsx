import type { ExportKind } from "../api/types";
import { Card } from "../components/ui";
import { useApp } from "../state";

const EXPORTS: { kind: ExportKind; title: string; desc: string }[] = [
  { kind: "bcf", title: "BCF 2.1", desc: "Un topic por issue abierto, para abrir en Navisworks, BIMcollab o Solibri." },
  { kind: "4d.csv", title: "CSV 4D", desc: "Una fila por elemento con nivel, partida, cantidad y fase sugerida." },
  { kind: "cobie.xlsx", title: "COBie (xlsx)", desc: "Hojas Contact, Facility, Floor, Type y Component." },
];

export default function ExportesPage() {
  const { client, selectedId, selected } = useApp();
  const demo = client.source === "mock";
  return (
    <div>
      <div className="page-head">
        <h1>Exportes</h1>
        <span className="muted">Versión {selected?.version_label ?? "—"}</span>
      </div>
      {demo && (
        <div className="alert alert-warn">
          Descargas deshabilitadas en modo demostración: los archivos los genera el backend.
        </div>
      )}
      <div className="rec-grid">
        {EXPORTS.map((x) => {
          const url = client.exportUrl(x.kind, selectedId);
          return (
            <Card key={x.kind} title={x.title}>
              <p>{x.desc}</p>
              {url ? (
                <a className="btn btn-primary" href={url} download>
                  Descargar {x.title}
                </a>
              ) : (
                <span className="tooltip-wrap" title="Disponible solo con backend conectado" tabIndex={0}>
                  <button className="btn btn-primary" disabled aria-disabled="true">
                    Descargar {x.title}
                  </button>
                </span>
              )}
            </Card>
          );
        })}
      </div>
    </div>
  );
}
