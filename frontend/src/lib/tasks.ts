import { useQuery } from "@tanstack/react-query";
import { api } from "./http";
import type { components } from "./api";

export type Task = components["schemas"]["TaskOut"];

const TERMINAL: Task["status"][] = ["SUCCESS", "FAILED", "RETRIED"];

/** The single source of truth for "this task will not change state again
 * without a new enqueue" — every caller that derives a busy/spinner flag
 * from task data must use this, not its own inline status list. Two
 * divergent copies is how a RETRIED task became a permanent stuck spinner
 * (US-26/27 fix). */
export function isTerminal(status: Task["status"]): boolean {
  return TERMINAL.includes(status);
}

/** Polls a background task (rank/parse/schedule) until it reaches a terminal status. */
export function useTask(taskId: string | undefined) {
  return useQuery<Task>({
    queryKey: ["tasks", taskId],
    queryFn: () => api.get<Task>(`/tasks/${taskId}`),
    enabled: !!taskId,
    refetchInterval: (query) =>
      query.state.data && isTerminal(query.state.data.status) ? false : 1500,
  });
}

export const UNSCHEDULED_REASONS: Record<string, string> = {
  NO_SLOT_IN_HORIZON:
    "No available slot in the next 14 days — check your interview availability in Scheduling.",
  ALREADY_SCHEDULED: "This candidate already has an interview scheduled.",
  SLOT_TIME_TAKEN: "That time was just taken — try again.",
  CALENDAR_FAILED: "Couldn't create the calendar event. Try again.",
  NOT_RANKED: "This candidate is no longer ranked.",
  CANDIDATE_NOT_FOUND: "Candidate not found.",
};

/** Short phrases for the grouped multi-candidate summary (TS-17) — the full
 * sentences in UNSCHEDULED_REASONS read correctly standalone but not when
 * joined ("2 This candidate already has an interview scheduled."). */
const UNSCHEDULED_REASON_SHORT: Record<string, string> = {
  NO_SLOT_IN_HORIZON: "no slot in the next 14 days",
  ALREADY_SCHEDULED: "already scheduled",
  SLOT_TIME_TAKEN: "slot time taken",
  CALENDAR_FAILED: "calendar failed",
  NOT_RANKED: "not ranked",
  CANDIDATE_NOT_FOUND: "candidate not found",
};

export interface ScheduleOutcome {
  variant: "success" | "error";
  message: string;
}

interface ScheduleResultSummary {
  scheduled: number;
  unscheduled: { reason: string }[];
}

function groupedReasonSummary(unscheduled: { reason: string }[]): string {
  const counts = new Map<string, number>();
  for (const { reason } of unscheduled) {
    counts.set(reason, (counts.get(reason) ?? 0) + 1);
  }
  return [...counts.entries()]
    .map(
      ([reason, count]) =>
        `${count} ${
          UNSCHEDULED_REASON_SHORT[reason] ??
          reason.toLowerCase().replace(/_/g, " ")
        }`,
    )
    .join(", ");
}

/** Pure decision of what to tell the recruiter once a CALENDAR_SYNC task
 * (from "Schedule interview"/"Schedule N interviews") has reached a terminal
 * state. Kept separate from the component so the mapping — including the
 * FAILED branch, the single-candidate branches (US-26/27 TC-04), and the
 * multi-candidate grouped-reason branch (TS-17) — is unit-testable without a
 * QueryClient or fetch mock. */
export function scheduleOutcome(task: Task): ScheduleOutcome {
  if (task.status === "FAILED") {
    return {
      variant: "error",
      message: task.error_message ?? "Couldn't schedule an interview.",
    };
  }

  const summary = task.result_summary as ScheduleResultSummary | null;
  const scheduled = summary?.scheduled ?? 0;
  const unscheduled = summary?.unscheduled ?? [];

  if (scheduled > 0 && unscheduled.length === 0) {
    return {
      variant: "success",
      message:
        scheduled === 1
          ? "Interview scheduled — invite sent."
          : `${scheduled} interviews scheduled — invites sent.`,
    };
  }

  // Exactly one candidate, nothing scheduled: the original single-reason
  // sentence reads better standalone than the grouped summary would.
  if (scheduled === 0 && unscheduled.length === 1) {
    const reason = unscheduled[0]?.reason;
    return {
      variant: "error",
      message:
        (reason && UNSCHEDULED_REASONS[reason]) ??
        "Couldn't schedule an interview.",
    };
  }

  if (unscheduled.length === 0) {
    return { variant: "error", message: "Couldn't schedule an interview." };
  }

  // A batch: some or all candidates couldn't be scheduled, for more than one
  // reason, or more than one candidate — the TC-04 case the backend was
  // built for and the UI never showed before TS-17.
  const reasonSummary = groupedReasonSummary(unscheduled);
  return {
    variant: scheduled > 0 ? "success" : "error",
    message:
      scheduled > 0
        ? `${scheduled} scheduled, ${unscheduled.length} could not be scheduled: ${reasonSummary}.`
        : `Could not schedule ${unscheduled.length} candidates: ${reasonSummary}.`,
  };
}
