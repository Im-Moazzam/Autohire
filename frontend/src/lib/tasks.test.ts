import { describe, expect, it } from "vitest";
import {
  isTerminal,
  scheduleOutcome,
  UNSCHEDULED_REASONS,
  type Task,
} from "./tasks";

function task(overrides: Partial<Task>): Task {
  return {
    task_id: "11111111-1111-1111-1111-111111111111",
    task_type: "CALENDAR_SYNC",
    status: "SUCCESS",
    started_at: "2026-09-03T10:00:00Z",
    completed_at: "2026-09-03T10:00:02Z",
    error_message: null,
    result_summary: null,
    ...overrides,
  };
}

describe("isTerminal", () => {
  it("treats SUCCESS, FAILED, and RETRIED as terminal", () => {
    expect(isTerminal("SUCCESS")).toBe(true);
    expect(isTerminal("FAILED")).toBe(true);
    expect(isTerminal("RETRIED")).toBe(true);
  });

  it("treats PENDING and RUNNING as non-terminal", () => {
    expect(isTerminal("PENDING")).toBe(false);
    expect(isTerminal("RUNNING")).toBe(false);
  });
});

describe("scheduleOutcome", () => {
  it("reports the backend error message on FAILED", () => {
    const outcome = scheduleOutcome(
      task({ status: "FAILED", error_message: "Calendar API unreachable" }),
    );
    expect(outcome).toEqual({
      variant: "error",
      message: "Calendar API unreachable",
    });
  });

  it("falls back to generic copy when FAILED has no error_message", () => {
    const outcome = scheduleOutcome(
      task({ status: "FAILED", error_message: null }),
    );
    expect(outcome).toEqual({
      variant: "error",
      message: "Couldn't schedule an interview.",
    });
  });

  it("reports success when at least one candidate was scheduled", () => {
    const outcome = scheduleOutcome(
      task({
        status: "SUCCESS",
        result_summary: { scheduled: 1, unscheduled: [] },
      }),
    );
    expect(outcome).toEqual({
      variant: "success",
      message: "Interview scheduled — invite sent.",
    });
  });

  it("surfaces NO_SLOT_IN_HORIZON as its specific, actionable copy — not a generic failure", () => {
    const outcome = scheduleOutcome(
      task({
        status: "SUCCESS",
        result_summary: {
          scheduled: 0,
          unscheduled: [
            { reason: "NO_SLOT_IN_HORIZON", full_name: "A", candidate_id: "x" },
          ],
        },
      }),
    );
    expect(outcome).toEqual({
      variant: "error",
      message: UNSCHEDULED_REASONS.NO_SLOT_IN_HORIZON,
    });
  });

  it("maps ALREADY_SCHEDULED to its specific copy", () => {
    const outcome = scheduleOutcome(
      task({
        status: "SUCCESS",
        result_summary: {
          scheduled: 0,
          unscheduled: [
            { reason: "ALREADY_SCHEDULED", full_name: "A", candidate_id: "x" },
          ],
        },
      }),
    );
    expect(outcome).toEqual({
      variant: "error",
      message: UNSCHEDULED_REASONS.ALREADY_SCHEDULED,
    });
  });

  it("falls back to generic copy for an unmapped reason", () => {
    const outcome = scheduleOutcome(
      task({
        status: "SUCCESS",
        result_summary: {
          scheduled: 0,
          unscheduled: [
            { reason: "SOMETHING_NEW", full_name: "A", candidate_id: "x" },
          ],
        },
      }),
    );
    expect(outcome).toEqual({
      variant: "error",
      message: "Couldn't schedule an interview.",
    });
  });

  it("falls back to generic copy when result_summary is null", () => {
    const outcome = scheduleOutcome(
      task({ status: "SUCCESS", result_summary: null }),
    );
    expect(outcome).toEqual({
      variant: "error",
      message: "Couldn't schedule an interview.",
    });
  });
});
