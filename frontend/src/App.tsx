import { useCallback, useEffect, useMemo, useState } from "react";
import { resolveClient, type ResolvedClient } from "./api/client";
import type { Snapshot } from "./api/types";
import { AppContext, type AppState } from "./state";
import { CdeBadge, ErrorBox, Loading } from "./components/ui";
import { formatDate } from "./format";
import SaludPage from "./pages/SaludPage";
import IssuesPage from "./pages/IssuesPage";
import RecomendacionesPage from "./pages/RecomendacionesPage";
import PresupuestoPage from "./pages/PresupuestoPage";
import ExportesPage from "./pages/ExportesPage";

const PAGES = [
  { path: "salud", label: "Salud del modelo", el: <SaludPage /> },
  { path: "issues", label: "Issues", el: <IssuesPage /> },
  { path: "recomendaciones", label: "Recomendaciones IA", el: <RecomendacionesPage /> },
  { path: "presupuesto", label: "Presupuesto 5D", el: <PresupuestoPage /> },
  { path: "exportes", label: "Exportes", el: <ExportesPage /> },
] as const;

function currentPath(): string {
  const p = window.location.hash.replace(/^#\/?/, "");
  return PAGES.some((x) => x.path === p) ? p : "salud";
}

export default function App() {
  const [resolved, setResolved] = useState<ResolvedClient>();
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [selectedId, setSelectedId] = useState<number>();
  const [error, setError] = useState<unknown>();
  const [version, setVersion] = useState(0);
  const [loaded, setLoaded] = useState(false);
  const [path, setPath] = useState(currentPath);

  useEffect(() => {
    const onHash = () => setPath(currentPath());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  useEffect(() => {
    resolveClient().then(setResolved, setError);
  }, []);

  const refreshSnapshots = useCallback(async () => {
    if (!resolved) return;
    try {
      const list = await resolved.client.listSnapshots();
      setSnapshots(list);
      setSelectedId((cur) => (cur !== undefined && list.some((s) => s.id === cur) ? cur : list[0]?.id));
      setVersion((v) => v + 1);
    } catch (e) {
      setError(e);
    } finally {
      setLoaded(true);
    }
  }, [resolved]);

  useEffect(() => {
    void refreshSnapshots();
  }, [refreshSnapshots]);

  const state: AppState | null = useMemo(
    () =>
      resolved
        ? {
            ...resolved,
            snapshots,
            selectedId,
            selected: snapshots.find((s) => s.id === selectedId),
            setSelectedId,
            refreshSnapshots,
            version,
          }
        : null,
    [resolved, snapshots, selectedId, refreshSnapshots, version],
  );

  if (error && !state) return <main className="page"><ErrorBox error={error} /></main>;
  if (!state) return <main className="page"><Loading label="Conectando con el backend…" /></main>;

  const page = PAGES.find((p) => p.path === path)!;
  return (
    <AppContext.Provider value={state}>
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">BIM</span>
          <div>
            <div className="brand-title">Agente Profesor BIM</div>
            <div className="brand-sub">Proyecto {state.selected?.project_code ?? "—"} · ISO 19650</div>
          </div>
        </div>
        <div className="topbar-right">
          {state.mockReason && (
            <span
              className="pill pill-demo"
              title={state.mockReason === "forzado" ? "VITE_USE_MOCK=true" : "El backend /api/health no respondió; se muestran datos de ejemplo."}
            >
              Datos de demostración
            </span>
          )}
          <label className="snap-select">
            <span>Versión</span>
            <select value={selectedId ?? ""} onChange={(e) => setSelectedId(Number(e.target.value))} disabled={snapshots.length === 0}>
              {snapshots.map((s, i) => (
                <option key={s.id} value={s.id}>
                  {s.version_label} · {s.cde_state} · {formatDate(s.created_at)}
                  {i === 0 ? " (última)" : ""}
                </option>
              ))}
            </select>
          </label>
          {state.selected && <CdeBadge state={state.selected.cde_state} />}
        </div>
      </header>
      <nav className="tabs" aria-label="Secciones">
        {PAGES.map((p) => (
          <a key={p.path} href={`#/${p.path}`} className={p.path === path ? "tab active" : "tab"} aria-current={p.path === path ? "page" : undefined}>
            {p.label}
          </a>
        ))}
      </nav>
      <main className="page">
        {error ? <ErrorBox error={error} onRetry={() => { setError(undefined); void refreshSnapshots(); }} /> : null}
        {!loaded ? (
          <Loading />
        ) : snapshots.length === 0 && !error ? (
          <div className="alert">Aún no hay snapshots. Envía uno desde el plugin de Revit.</div>
        ) : (
          page.el
        )}
      </main>
    </AppContext.Provider>
  );
}
