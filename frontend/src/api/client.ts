// Cliente HTTP tipado con los tipos generados (src/api/schema.d.ts) + fallback a datos de demostración.
import { mockApi } from "./mock";
import {
  ApiError,
  type ApiClient,
  type Budget,
  type BudgetDiff,
  type CdeState,
  type ElementThread,
  type ExportKind,
  type Feedback,
  type Health,
  type Issue,
  type IssueFilters,
  type Recommendation,
  type Snapshot,
  type Stats,
} from "./types";

type FetchFn = typeof fetch;
type Query = Record<string, string | number | undefined>;

function qs(params: Query = {}): string {
  const u = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== "") u.set(k, String(v));
  const s = u.toString();
  return s ? `?${s}` : "";
}

export function createHttpClient(base = "/api", fetchFn: FetchFn = (...a) => fetch(...a)): ApiClient {
  async function request<T>(method: string, path: string, query?: Query, body?: unknown): Promise<T> {
    const res = await fetchFn(`${base}${path}${qs(query)}`, {
      method,
      headers: body === undefined ? { Accept: "application/json" } : { "Content-Type": "application/json", Accept: "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    if (!res.ok) {
      let detail = res.statusText || "Error";
      try {
        const data = (await res.json()) as { detail?: unknown };
        if (typeof data.detail === "string") detail = data.detail;
        else if (data.detail !== undefined) detail = JSON.stringify(data.detail);
      } catch {
        /* cuerpo no JSON */
      }
      throw new ApiError(res.status, detail);
    }
    return (await res.json()) as T;
  }

  return {
    source: "api",
    health: () => request<Health>("GET", "/health"),
    listSnapshots: () => request<Snapshot[]>("GET", "/snapshots"),
    setCdeState: (id: number, cde_state: CdeState) =>
      request<Snapshot>("PATCH", `/snapshots/${id}/cde-state`, undefined, { cde_state }),
    listIssues: (f: IssueFilters = {}) => request<Issue[]>("GET", "/issues", { ...f }),
    getElementThread: (guid: string) => request<ElementThread>("GET", `/elements/${encodeURIComponent(guid)}/thread`),
    listFeedback: () => request<Feedback[]>("GET", "/feedback"),
    getStats: (id?: number) => request<Stats>("GET", "/stats", { snapshot_id: id }),
    getBudget: (id?: number) => request<Budget>("GET", "/budget", { snapshot_id: id }),
    getBudgetDiff: (from: number, to: number) =>
      request<BudgetDiff>("GET", "/budget/diff", { from_snapshot_id: from, to_snapshot_id: to }),
    getRecommendations: (id?: number) => request<Recommendation[]>("GET", "/ai/recommendations", { snapshot_id: id }),
    exportUrl: (kind: ExportKind, id?: number) => `${base}/export/${kind}${qs({ snapshot_id: id })}`,
  };
}

export interface ResolvedClient {
  client: ApiClient;
  health: Health;
  /** Motivo por el que se usa el mock (null si hay backend). */
  mockReason: null | "forzado" | "sin_backend";
}

/**
 * Decide qué cliente usar: mock si VITE_USE_MOCK=true o si /api/health falla.
 */
export async function resolveClient(opts: {
  useMock?: boolean;
  http?: ApiClient;
  timeoutMs?: number;
} = {}): Promise<ResolvedClient> {
  const useMock = opts.useMock ?? import.meta.env.VITE_USE_MOCK === "true";
  if (useMock) return { client: mockApi, health: await mockApi.health(), mockReason: "forzado" };
  const http = opts.http ?? createHttpClient();
  try {
    const health = await withTimeout(http.health(), opts.timeoutMs ?? 2500);
    if (health?.status !== "ok") throw new Error("health no ok");
    return { client: http, health, mockReason: null };
  } catch {
    return { client: mockApi, health: await mockApi.health(), mockReason: "sin_backend" };
  }
}

function withTimeout<V>(p: Promise<V>, ms: number): Promise<V> {
  return new Promise<V>((resolve, reject) => {
    const t = setTimeout(() => reject(new Error("timeout")), ms);
    p.then(
      (v) => { clearTimeout(t); resolve(v); },
      (e) => { clearTimeout(t); reject(e); },
    );
  });
}
