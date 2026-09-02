import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./http";
import type { components } from "./api";
import type { Status } from "../components/ui/StatusBadge";
import type { Task } from "./tasks";

export type SchedulingPreferences =
  components["schemas"]["SchedulingPreferencesOut"];
export type SchedulingPreferencesInput =
  components["schemas"]["SchedulingPreferencesIn"];
export type InterviewSlot = components["schemas"]["InterviewSlotOut"];
export type SlotStatus = components["schemas"]["SlotStatus"];
export type Weekday = components["schemas"]["Weekday"];
type InterviewPage = components["schemas"]["Page_InterviewSlotOut_"];

export const WEEKDAY_LABELS: Record<Weekday, string> = {
  MONDAY: "Mon",
  TUESDAY: "Tue",
  WEDNESDAY: "Wed",
  THURSDAY: "Thu",
  FRIDAY: "Fri",
  SATURDAY: "Sat",
  SUNDAY: "Sun",
};

export const WEEKDAY_ORDER: Weekday[] = [
  "MONDAY",
  "TUESDAY",
  "WEDNESDAY",
  "THURSDAY",
  "FRIDAY",
  "SATURDAY",
  "SUNDAY",
];

export const SLOT_STATUS_LABELS: Record<SlotStatus, Status> = {
  PENDING: "Scheduled",
  CONFIRMED: "Confirmed",
  DECLINED: "Declined",
  RESCHEDULED: "Reschedule Requested",
  CANCELLED: "Cancelled",
};

export function useSchedulingPreferences() {
  return useQuery<SchedulingPreferences>({
    queryKey: ["scheduling", "preferences"],
    queryFn: () => api.get<SchedulingPreferences>("/scheduling/preferences"),
  });
}

export function useUpdateSchedulingPreferences() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: SchedulingPreferencesInput) =>
      api.put<SchedulingPreferences>("/scheduling/preferences", payload),
    onSuccess: (data) => {
      queryClient.setQueryData(["scheduling", "preferences"], data);
    },
  });
}

export interface InterviewListFilters {
  job_id?: string;
  status?: SlotStatus;
  page?: number;
}

export const INTERVIEWS_PAGE_SIZE = 20;

export function useInterviews(filters: InterviewListFilters) {
  const params = new URLSearchParams({
    size: String(INTERVIEWS_PAGE_SIZE),
    page: String(filters.page ?? 1),
  });
  if (filters.job_id) params.set("job_id", filters.job_id);
  if (filters.status) params.set("status", filters.status);

  return useQuery<InterviewPage>({
    queryKey: ["interviews", filters],
    queryFn: () => api.get<InterviewPage>(`/interviews?${params.toString()}`),
  });
}

export function useScheduleInterviews() {
  return useMutation({
    mutationFn: (payload: { job_id: string; candidate_ids: string[] }) =>
      api.post<Task>("/interviews", payload),
  });
}
