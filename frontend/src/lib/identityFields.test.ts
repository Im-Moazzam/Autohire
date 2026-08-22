import { describe, expect, it } from "vitest";
import { hasIdentityFields } from "./identityFields";
import cases from "../../../docs/identity-fields-cases.json";

/** Golden file shared with backend/tests/test_identity_fields_contract.py
 * (issue #23) — a case that passes there but fails here (or vice versa) means
 * the two implementations have drifted and both need updating together. */
describe("hasIdentityFields matches the shared contract", () => {
  for (const testCase of cases.cases as {
    labels: string[];
    email: boolean;
    name: boolean;
  }[]) {
    it(`labels=${JSON.stringify(testCase.labels)}`, () => {
      const result = hasIdentityFields(testCase.labels);
      expect(result.email).toBe(testCase.email);
      expect(result.name).toBe(testCase.name);
    });
  }
});
