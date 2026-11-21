import { describe, expect, it } from "vitest";
import { RULE_NAMES } from "./rules";

describe("reglas desde data/rules.json", () => {
  it("expone el nombre de cada regla", () => {
    expect(RULE_NAMES.R06).toBe("Nombre de archivo fuera de ISO 19650");
  });
});
