import { createContext, useCallback, useContext, useEffect, useState, type DependencyList } from "react";
import type { ResolvedClient } from "./api/client";
import type { ApiClient, Snapshot } from "./api/types";

export interface AppState extends ResolvedClient {
  snapshots: Snapshot[];
  selectedId: number | undefined;
  selected: Snapshot | undefined;
  setSelectedId: (id: number) => void;
  refreshSnapshots: () => Promise<void>;
  /** Cambia cada vez que algo muta (estado CDE) para recargar vistas. */
  version: number;
}

export const AppContext = createContext<AppState | null>(null);

export function useApp(): AppState {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error("useApp fuera de AppContext");
  return ctx;
}

export interface AsyncState<V> {
  data: V | undefined;
  error: unknown;
  loading: boolean;
  reload: () => void;
}

/** Ejecuta una llamada al API y la repite cuando cambian las dependencias. */
export function useApi<V>(fn: (c: ApiClient) => Promise<V>, deps: DependencyList): AsyncState<V> {
  const { client, version } = useApp();
  const [data, setData] = useState<V>();
  const [error, setError] = useState<unknown>();
  const [loading, setLoading] = useState(true);
  const [tick, setTick] = useState(0);
  const reload = useCallback(() => setTick((t) => t + 1), []);
  useEffect(() => {
    let alive = true;
    setLoading(true);
    setError(undefined);
    fn(client).then(
      (v) => alive && (setData(v), setLoading(false)),
      (e) => alive && (setError(e), setLoading(false)),
    );
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [client, version, tick, ...deps]);
  return { data, error, loading, reload };
}
