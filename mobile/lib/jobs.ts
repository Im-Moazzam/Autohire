import { useQuery } from "@tanstack/react-query";
import type { components } from "./api";
import { api } from "./http";

export type Job = components["schemas"]["JobOut"];
export type JobDetail = components["schemas"]["JobDetailOut"];
export type JobStatus = components["schemas"]["JobStatus"];
type JobPage = components["schemas"]["Page_JobOut_"];

export const JOB_STATUS_LABELS: Record<JobStatus, string> = {
  DRAFT: "Draft",
  LIVE: "Live",
  CLOSED: "Closed",
  PROCESSED: "Processed",
};

export const JOB_STATUS_COLORS: Record<JobStatus, string> = {
  DRAFT: "muted",
  LIVE: "success",
  CLOSED: "navy",
  PROCESSED: "primary",
};

export function useJobs() {
  return useQuery<JobPage>({
    queryKey: ["jobs"],
    queryFn: () => api.get<JobPage>("/jobs?size=100"),
  });
}

export function useJob(jobId: string | undefined) {
  return useQuery<JobDetail>({
    queryKey: ["jobs", jobId],
    queryFn: () => api.get<JobDetail>(`/jobs/${jobId}`),
    enabled: !!jobId,
  });
}
