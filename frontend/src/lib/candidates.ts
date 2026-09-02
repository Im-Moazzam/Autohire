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
  // No "INVITED" here: scheduling a real interview must go through
  // POST /interviews (creates a real Calendar event + sends the invite
  // email) — see the dedicated "Schedule interview" action, not a bare
  // status PATCH that would silently fake having scheduled anything.
  RANKED: ["REJECTED"],
  INVITED: ["REJECTED"],
  RESCHEDULED: ["REJECTED"],
  CONFIRMED: [],
  DECLINED: [],
  // REJECTED is handled separately by nextStatusOptions below — its one
  // legal target is never a fixed value here, it's whatever
  // restorable_status says (SUBMITTED/PARSED/PARSE_ERROR/RANKED), computed
  // server-side from real data. DECLINED stays terminal — that's the
  // candidate's own answer.
  REJECTED: [],
};

/** REJECTED's single legal target is dynamic — restorable_status (from the
 * API, derived from real data: an ai_analysis_results row, a populated
 * resume_text, a parse_error) is what submission_status would be if this
 * candidate had never been rejected. Hardcoding a fixed target here would
 * repeat the exact bug this replaced: claiming a parse/rank that never
 * happened. Every other current status keeps its static transition set. */
export function nextStatusOptions(
  current: SubmissionStatus,
  restorableStatus?: SubmissionStatus,
): SubmissionStatus[] {
  if (current === "REJECTED") return restorableStatus ? [restorableStatus] : [];
  return LEGAL_TRANSITIONS[current] ?? [];
}

/** Any REJECTED -> X transition is an undo, regardless of which status X
 * turns out to be (SUBMITTED/PARSED/PARSE_ERROR/RANKED) — "Mark Ranked"
 * would read like a fabricated re-rank, "Undo rejection" is accurate for
 * all of them. Every other transition keeps the default "Mark {label}". */
export function statusActionLabel(
  target: SubmissionStatus,
  from: SubmissionStatus,
): string {
  if (from === "REJECTED") return "Undo rejection";
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
