import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, API_URL } from "./http";
import type { components } from "./api";
import type { Status } from "../components/ui/StatusBadge";

const API_ORIGIN = API_URL.replace(/\/api\/v1$/, "");

/** resume_url is either an absolute Drive link or a backend-relative local
 * download path (/api/v1/candidates/{id}/resume) — the latter needs the API's
 * origin prepended since the frontend runs on a different port in dev. */
export function resumeHref(url: string | null | undefined): string | null {
  if (!url) return null;
  return url.startsWith("/api/v1") ? `${API_ORIGIN}${url}` : url;
}

export type Candidate = components["schemas"]["CandidateOut"];
export type CandidateDetail = components["schemas"]["CandidateDetailOut"];
export type RankedCandidate = components["schemas"]["RankedCandidateOut"];
export type SubmissionStatus = components["schemas"]["SubmissionStatus"];
type CandidatePage = components["schemas"]["Page_CandidateOut_"];
type RankedCandidatePage = components["schemas"]["Page_RankedCandidateOut_"];

export const SUBMISSION_STATUS_LABELS: Record<SubmissionStatus, Status> = {
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

// Mirrors backend/app/services/candidate_service.py::_LEGAL_TRANSITIONS —
// client-side copy only gates which buttons render; the server is still the
// authority and a stale copy just means a 409 the user retries against.
const LEGAL_TRANSITIONS: Record<SubmissionStatus, SubmissionStatus[]> = {
  SUBMITTED: ["REJECTED"],
  PARSE_ERROR: ["REJECTED"],
  PARSED: ["REJECTED"],
  RANKED: ["INVITED", "REJECTED"],
  INVITED: ["REJECTED"],
  RESCHEDULED: ["REJECTED"],
  CONFIRMED: [],
  DECLINED: [],
  // The one back-edge: a recruiter can undo an accidental rejection. Lands
  // on PARSED, not RANKED — the ranked list is an INNER JOIN against
  // ai_analysis_results, so a RANKED status with no analysis row would be a
  // candidate the ranked list could never actually show. PARSED accurately
  // means "eligible for the next ranking run," not "already ranked."
  // Deliberately no direct REJECTED -> INVITED shortcut: undo first, same
  // path as any other candidate — one obvious way back in, not two.
  // DECLINED stays terminal — that's the candidate's own answer.
  REJECTED: ["PARSED"],
};

export function nextStatusOptions(
  current: SubmissionStatus,
): SubmissionStatus[] {
  return LEGAL_TRANSITIONS[current] ?? [];
}

/** "Mark Parsed" reads like a no-op for the REJECTED -> PARSED edge — it's
 * actually undoing the rejection. Every other transition keeps the default
 * "Mark {label}" wording. */
export function statusActionLabel(
  target: SubmissionStatus,
  from: SubmissionStatus,
): string {
  if (from === "REJECTED" && target === "PARSED") return "Undo rejection";
  return `Mark ${SUBMISSION_STATUS_LABELS[target]}`;
}

export interface CandidateListFilters {
  submission_status?: SubmissionStatus;
  q?: string;
}

export function useCandidates(
  jobId: string | undefined,
  filters: CandidateListFilters,
) {
  const params = new URLSearchParams({ size: "100" });
  if (filters.submission_status)
    params.set("submission_status", filters.submission_status);
  if (filters.q) params.set("q", filters.q);

  return useQuery<CandidatePage>({
    queryKey: ["candidates", jobId, filters],
    queryFn: () =>
      api.get<CandidatePage>(`/jobs/${jobId}/candidates?${params.toString()}`),
    enabled: !!jobId,
  });
}

export function useRankedCandidates(jobId: string | undefined) {
  return useQuery<RankedCandidatePage>({
    queryKey: ["candidates", jobId, "ranked"],
    queryFn: () =>
      api.get<RankedCandidatePage>(`/jobs/${jobId}/candidates/ranked?size=100`),
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
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["candidates", jobId] });
    },
  });
}
