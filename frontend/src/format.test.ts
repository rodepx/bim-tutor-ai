import { describe, expect, it } from "vitest";
import { conformanceTone, formatPEN, formatPct, formatQty, formatSignedPEN, formatSignedPct, shortGuid } from "./format";

describe("formato es-PE", () => {
  it("formatea soles con 2 decimales", () => {
    expect(formatPEN(1234.5)).toBe("S/ 1,234.50");
    expect(formatPEN(0)).toBe("S/ 0.00");
    expect(formatPEN(null)).toBe("—");
  });
  it("antepone signo a montos y porcentajes", () => {
    expect(formatSignedPEN(10)).toBe("+S/ 10.00");
    expect(formatSignedPEN(-2500.456)).toBe("−S/ 2,500.46");
    expect(formatSignedPct(3.25)).toBe("+3.3 %");
    expect(formatSignedPct(null)).toBe("—");
  });
  it("formatea cantidades y porcentajes", () => {
    expect(formatQty(18.4)).toBe("18.40");
    expect(formatPct(87.54)).toBe("87.5 %");
  });
  it("clasifica la conformidad", () => {
    expect(conformanceTone(98)).toBe("ok");
    expect(conformanceTone(85)).toBe("warn");
    expect(conformanceTone(50)).toBe("bad");
  });
  it("acorta GUIDs largos", () => {
    expect(shortGuid("8a1f3c2e-5b7d-4e9a-b1c4-0f6d2e9a3c01-0004a125")).toBe("8a1f3c2e…04a125");
  });
});
