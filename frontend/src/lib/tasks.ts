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

export interface ScheduleOutcome {
  variant: "success" | "error";
  message: string;
}

interface ScheduleResultSummary {
  scheduled: number;
  unscheduled: { reason: string }[];
}

/** Pure decision of what to tell the recruiter once a CALENDAR_SYNC task
 * (from "Schedule interview") has reached a terminal state. Kept separate
 * from the component so the mapping — including the FAILED branch and the
 * "0 scheduled, reported explicitly" branch (US-26/27 TC-04) — is
 * unit-testable without a QueryClient or fetch mock. */
export function scheduleOutcome(task: Task): ScheduleOutcome {
  if (task.status === "FAILED") {
    return {
      variant: "error",
      message: task.error_message ?? "Couldn't schedule an interview.",
    };
  }

  const summary = task.result_summary as ScheduleResultSummary | null;
  if (summary?.scheduled) {
    return {
      variant: "success",
      message: "Interview scheduled — invite sent.",
    };
  }

  const reason = summary?.unscheduled[0]?.reason;
  return {
    variant: "error",
    message:
      (reason && UNSCHEDULED_REASONS[reason]) ??
      "Couldn't schedule an interview.",
  };
}
