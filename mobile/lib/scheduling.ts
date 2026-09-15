import { useQuery } from "@tanstack/react-query";
import type { components } from "./api";
import { api } from "./http";

export type InterviewSlot = components["schemas"]["InterviewSlotOut"];
export type SlotStatus = components["schemas"]["SlotStatus"];
type InterviewPage = components["schemas"]["Page_InterviewSlotOut_"];

export const SLOT_STATUS_LABELS: Record<SlotStatus, string> = {
  PENDING: "Scheduled",
  CONFIRMED: "Confirmed",
  DECLINED: "Declined",
  RESCHEDULED: "Reschedule Requested",
  CANCELLED: "Cancelled",
};

export const SLOT_STATUS_COLORS: Record<SlotStatus, string> = {
  PENDING: "primary",
  CONFIRMED: "success",
  DECLINED: "warning",
  RESCHEDULED: "cyan",
  CANCELLED: "muted",
};

/** Confirming/cancelling a slot from the recruiter side is a deliberate
 * backend stub (PATCH /interviews/{id} always 501s — "Phase 2, not
 * implemented", backend/app/api/routes/interviews.py) — mobile is
 * view-only here for the same reason the web Scheduling screen is. */
export function useInterviews() {
  return useQuery<InterviewPage>({
    queryKey: ["interviews"],
    queryFn: () => api.get<InterviewPage>("/interviews?size=100"),
  });
}
