import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./http";
import type { components } from "./api";
import type { Status } from "../components/ui/StatusBadge";

export type Job = components["schemas"]["JobOut"];
export type JobDetail = components["schemas"]["JobDetailOut"];
export type JobStatus = components["schemas"]["JobStatus"];
type JobPage = components["schemas"]["Page_JobOut_"];

export const JOB_STATUS_LABELS: Record<JobStatus, Status> = {
  DRAFT: "Draft",
  LIVE: "Live",
  CLOSED: "Closed",
  PROCESSED: "Processed",
};

export interface JobListFilters {
  status?: JobStatus;
  q?: string;
}

/** Mirrors task_service.enqueue_resume_parse's guard exactly (TS-06/R-01):
 * the backend only accepts a CLOSED job with at least one candidate. */
export function canProcessJob(job: Pick<Job, "status" | "submission_count">): {
  allowed: boolean;
  reason?: string;
} {
  if (job.status !== "CLOSED") {
    return { allowed: false, reason: "Only closed jobs can be processed" };
  }
  if (job.submission_count === 0) {
    return { allowed: false, reason: "No applications to process yet" };
  }
  return { allowed: true };
}

export function useJobs(filters: JobListFilters) {
  const params = new URLSearchParams({ size: "100" });
  if (filters.status) params.set("status", filters.status);
  if (filters.q) params.set("q", filters.q);

  return useQuery<JobPage>({
    queryKey: ["jobs", filters],
    queryFn: () => api.get<JobPage>(`/jobs?${params.toString()}`),
  });
}

export function useJob(jobId: string | undefined) {
  return useQuery<JobDetail>({
    queryKey: ["jobs", jobId],
    queryFn: () => api.get<JobDetail>(`/jobs/${jobId}`),
    enabled: !!jobId,
  });
}

export function useCreateJob() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: {
      job_title: string;
      job_description: string;
      template_id: string;
      expires_at: string;
    }) => api.post<JobDetail>("/jobs", payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["jobs"] }),
  });
}

export function useUpdateJob(jobId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (
      payload: Partial<{
        job_title: string;
        job_description: string;
        expires_at: string;
        is_accepting_responses: boolean;
        status: JobStatus;
      }>,
    ) => api.patch<JobDetail>(`/jobs/${jobId}`, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
      queryClient.invalidateQueries({ queryKey: ["jobs", jobId] });
    },
  });
}

export function useTriggerProcess() {
  return useMutation({
    mutationFn: (jobId: string) => api.post(`/jobs/${jobId}/process`),
  });
}
