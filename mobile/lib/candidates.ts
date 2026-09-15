import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { components } from "./api";
import { api } from "./http";

export type Candidate = components["schemas"]["CandidateOut"];
export type CandidateDetail = components["schemas"]["CandidateDetailOut"];
export type SubmissionStatus = components["schemas"]["SubmissionStatus"];
type CandidatePage = components["schemas"]["Page_CandidateOut_"];

export const SUBMISSION_STATUS_LABELS: Record<SubmissionStatus, string> = {
  SUBMITTED: "Submitted",
  PARSED: "Parsed",
  RANKED: "Ranked",
  INVITED: "Interview Invited",
  CONFIRMED: "Confirmed",
  DECLINED: "Declined",
  REJECTED: "Rejected",
  RESCHEDULED: "Reschedule Requested",
  PARSE_ERROR: "Parse Error",
};

export const SUBMISSION_STATUS_COLORS: Record<SubmissionStatus, string> = {
  SUBMITTED: "muted",
  PARSED: "cyan",
  RANKED: "ai",
  INVITED: "navy",
  CONFIRMED: "success",
  DECLINED: "muted",
  REJECTED: "error",
  RESCHEDULED: "warning",
  PARSE_ERROR: "error",
};

/** Mirrors frontend/src/lib/candidates.ts (which mirrors the backend's
 * _LEGAL_TRANSITIONS) — mobile only exposes reject / undo-rejection, so this
 * only needs to answer "is reject legal" and "what does undo restore to." */
export function canReject(status: SubmissionStatus): boolean {
  return !["CONFIRMED", "DECLINED", "REJECTED"].includes(status);
}

export function useCandidates(jobId: string | undefined) {
  return useQuery<CandidatePage>({
    queryKey: ["candidates", jobId],
    queryFn: () => api.get<CandidatePage>(`/jobs/${jobId}/candidates?size=100`),
    enabled: !!jobId,
  });
}

export function useCandidate(candidateId: string | undefined) {
  return useQuery<CandidateDetail>({
    queryKey: ["candidates", "detail", candidateId],
    queryFn: () => api.get<CandidateDetail>(`/candidates/${candidateId}`),
    enabled: !!candidateId,
  });
}

export function useUpdateCandidateStatus(jobId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      candidateId,
      status,
    }: {
      candidateId: string;
      status: SubmissionStatus;
    }) =>
      api.patch<CandidateDetail>(`/candidates/${candidateId}`, {
        submission_status: status,
      }),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["candidates", jobId] });
      queryClient.invalidateQueries({
        queryKey: ["candidates", "detail", variables.candidateId],
      });
    },
  });
}
