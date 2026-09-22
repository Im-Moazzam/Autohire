import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./http";
import type { components } from "./api";
import type { Status } from "../components/ui/StatusBadge";

export type AdminRecruiter = components["schemas"]["AdminRecruiterOut"];
export type AdminTask = components["schemas"]["AdminTaskOut"];
export type TaskStatus = components["schemas"]["TaskStatus"];
export type TaskType = components["schemas"]["TaskType"];
type AdminRecruiterPage = components["schemas"]["Page_AdminRecruiterOut_"];
type AdminTaskPage = components["schemas"]["Page_AdminTaskOut_"];

export const ACCOUNT_STATE_LABELS: Record<
  AdminRecruiter["account_state"],
  Status
> = {
  ACTIVE: "Active",
  SUSPENDED: "Suspended",
  REAUTH_REQUIRED: "Reauth Required",
};

export const TASK_STATUS_LABELS: Record<TaskStatus, Status> = {
  PENDING: "Scheduled",
  RUNNING: "Processing",
  SUCCESS: "Confirmed",
  FAILED: "Failed",
  RETRIED: "Retried",
};

export const ADMIN_PAGE_SIZE = 20;

export function useAdminRecruiters(page: number) {
  return useQuery<AdminRecruiterPage>({
    queryKey: ["admin", "recruiters", page],
    queryFn: () =>
      api.get<AdminRecruiterPage>(
        `/admin/recruiters?page=${page}&size=${ADMIN_PAGE_SIZE}`,
      ),
  });
}

export interface AdminTaskFilters {
  status?: TaskStatus;
  task_type?: TaskType;
  page?: number;
}

export function useAdminTasks(filters: AdminTaskFilters) {
  const params = new URLSearchParams({
    size: String(ADMIN_PAGE_SIZE),
    page: String(filters.page ?? 1),
  });
  if (filters.status) params.set("status", filters.status);
  if (filters.task_type) params.set("task_type", filters.task_type);

  return useQuery<AdminTaskPage>({
    queryKey: ["admin", "tasks", filters],
    queryFn: () => api.get<AdminTaskPage>(`/admin/tasks?${params.toString()}`),
  });
}

export function useSuspendRecruiter() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (recruiterId: string) =>
      api.post(`/admin/recruiters/${recruiterId}/suspend`),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["admin", "recruiters"] }),
  });
}

export function useReactivateRecruiter() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (recruiterId: string) =>
      api.post(`/admin/recruiters/${recruiterId}/reactivate`),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["admin", "recruiters"] }),
  });
}
