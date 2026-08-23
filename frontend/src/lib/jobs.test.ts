import { describe, expect, it } from "vitest";
import { canProcessJob } from "./jobs";

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
});
