import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { canProcessJob, dateToExpiresAt, expiresAtToDateInput } from "./jobs";

// vitest runs on Node; tsconfig.app.json (types: ["vite/client"]) doesn't
// declare Node's ambient `process`, so a minimal local declaration avoids
// pulling in @types/node project-wide for one test file.
declare const process: { env: Record<string, string | undefined> };

describe("dateToExpiresAt / expiresAtToDateInput round trip (TS-06/R-08)", () => {
  const originalTZ = process.env.TZ;

  beforeEach(() => {
    process.env.TZ = "America/New_York"; // UTC-4/-5, a negative offset
  });

  afterEach(() => {
    process.env.TZ = originalTZ;
  });

  it("returns the same local date that was entered", () => {
    const entered = "2026-03-15";
    const iso = dateToExpiresAt(entered);
    expect(expiresAtToDateInput(iso)).toBe(entered);
  });
});

describe("canProcessJob", () => {
  it("LIVE with candidates -> false", () => {
    expect(canProcessJob({ status: "LIVE", submission_count: 3 }).allowed).toBe(
      false,
    );
  });

  it("CLOSED with zero candidates -> false", () => {
    expect(
      canProcessJob({ status: "CLOSED", submission_count: 0 }).allowed,
    ).toBe(false);
  });

  it("CLOSED with candidates -> true", () => {
    expect(
      canProcessJob({ status: "CLOSED", submission_count: 1 }).allowed,
    ).toBe(true);
  });

  it("DRAFT -> false", () => {
    expect(
      canProcessJob({ status: "DRAFT", submission_count: 5 }).allowed,
    ).toBe(false);
  });

  it("PROCESSED with candidates -> true (re-running the pipeline)", () => {
    expect(
      canProcessJob({ status: "PROCESSED", submission_count: 1 }).allowed,
    ).toBe(true);
  });

  it("PROCESSED with zero candidates -> false", () => {
    expect(
      canProcessJob({ status: "PROCESSED", submission_count: 0 }).allowed,
    ).toBe(false);
  });
});
