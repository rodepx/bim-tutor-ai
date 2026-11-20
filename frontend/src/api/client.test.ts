import { beforeEach, describe, expect, it } from "vitest";
import { createHttpClient, resolveClient } from "./client";
import { mockApi, resetMockStore } from "./mock";
import { ApiError } from "./types";

const okHealth = () => new Response(JSON.stringify({ status: "ok", version: "1", llm_mode: "openrouter" }), { status: 200 });

describe("resolveClient", () => {
  it("usa el mock si se fuerza", async () => {
    const r = await resolveClient({ useMock: true });
    expect(r.client.source).toBe("mock");
    expect(r.mockReason).toBe("forzado");
  });
  it("cae al mock si /api/health falla", async () => {
    const http = createHttpClient("/api", async () => { throw new TypeError("fetch failed"); });
    const r = await resolveClient({ useMock: false, http });
    expect(r.client.source).toBe("mock");
    expect(r.mockReason).toBe("sin_backend");
  });
  it("usa el backend si /api/health responde", async () => {
    const http = createHttpClient("/api", async () => okHealth());
    const r = await resolveClient({ useMock: false, http });
    expect(r.client.source).toBe("api");
    expect(r.health.llm_mode).toBe("openrouter");
  });
});

describe("cliente HTTP", () => {
  it("arma query y expone el detail de errores 409", async () => {
    const calls: string[] = [];
    const http = createHttpClient("/api", async (input, init) => {
      calls.push(`${init?.method} ${String(input)}`);
      return new Response(JSON.stringify({ detail: "hay 3 errores" }), { status: 409 });
    });
    await expect(http.setCdeState(1, "SHARED")).rejects.toMatchObject({ status: 409, detail: "hay 3 errores" });
    expect(calls[0]).toBe("PATCH /api/snapshots/1/cde-state");
    expect(http.exportUrl("4d.csv", 2)).toBe("/api/export/4d.csv?snapshot_id=2");
  });
});

describe("mock", () => {
  beforeEach(() => resetMockStore());
  it("v1 WIP no puede pasar a SHARED (409); v2 sí está sin errores", async () => {
    await expect(mockApi.setCdeState(1, "SHARED")).rejects.toBeInstanceOf(ApiError);
    const s2 = await mockApi.getStats(2);
    expect(s2.can_move_to_shared).toBe(true);
    const s1 = await mockApi.getStats(1);
    expect(s1.can_move_to_shared).toBe(false);
  });
  it("tiene issues de las 7 reglas y un presupuesto consistente", async () => {
    const issues = await mockApi.listIssues({ snapshot_id: 1 });
    expect(new Set(issues.map((i) => i.rule_id)).size).toBe(7);
    const b = await mockApi.getBudget(2);
    const sum = Math.round(b.lines.reduce((a, l) => a + l.subtotal, 0) * 100) / 100;
    expect(b.total).toBe(sum);
    const d = await mockApi.getBudgetDiff(1, 2);
    expect(d.delta_total).toBeCloseTo(d.total_to - d.total_from, 2);
    expect(d.lines.some((l) => l.change === "added") && d.lines.some((l) => l.change === "removed")).toBe(true);
  });
});
