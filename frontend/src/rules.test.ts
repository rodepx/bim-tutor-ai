import { describe, expect, it } from "vitest";
import { RULE_NAMES, RULE_SEVERITY, openBySeverity } from "./rules";

describe("reglas desde data/rules.json", () => {
  it("expone nombre y severidad", () => {
    expect(RULE_NAMES.R06).toBe("Nombre de archivo fuera de ISO 19650");
    expect(RULE_SEVERITY.R02).toBe("error");
    expect(RULE_SEVERITY.R06).toBe("warning");
  });
  it("cuenta abiertos por severidad incluyendo reglas de documento (R06)", () => {
    const row = (rule_id: string, open_count: number) => ({ rule_id, rule_name: "", open_count, fixed_count: 0, feedback_count: 0 });
    expect(openBySeverity([row("R01", 2), row("R02", 3), row("R04", 4), row("R06", 1), row("RX", 9)])).toEqual({ errors: 5, warnings: 5 });
  });
});
