import { describe, expect, it } from "vitest";
import { CDE_LABELS, FEEDBACK_REASON_LABELS, RULE_NAMES } from "./rules";

describe("reglas desde data/rules.json", () => {
  it("expone el nombre de cada regla", () => {
    expect(RULE_NAMES.R06).toBe("Nombre de archivo fuera de ISO 19650");
  });
  it("etiquetas sin doble codificación UTF-8", () => {
    expect(CDE_LABELS.SHARED).toBe("SHARED · Compartido");
    expect(FEEDBACK_REASON_LABELS.no_encuentro_codigo).toBe("No encuentro el código");
  });
});
