import { useMutation, useQuery } from "@tanstack/react-query";
import { API_URL, ApiError } from "./http";
import type { components } from "./api";

export type PublicJob = components["schemas"]["PublicJobOut"];
export type TemplateField = components["schemas"]["TemplateFieldOut"];
export type ApplySuccess = components["schemas"]["ApplySuccessOut"];

/** No credentials/session — these are the two unauthenticated endpoints in
 * the system (ADR-004 P1), so lib/http.ts's cookie-carrying `api` helper
 * doesn't apply, and a raw JSON fetch wouldn't support the resume upload's
 * multipart body either. */
async function publicRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, init);
  const body = res.status === 204 ? null : await res.json().catch(() => null);
  if (!res.ok) {
    throw new ApiError(
      `Request to ${path} failed with ${res.status}`,
      res.status,
      body,
    );
  }
  return body as T;
}

export function usePublicJob(slug: string | undefined) {
  return useQuery<PublicJob>({
    queryKey: ["public-job", slug],
    queryFn: () => publicRequest<PublicJob>(`/public/apply/${slug}`),
    enabled: !!slug,
    retry: false,
  });
}

export function useSubmitApplication(slug: string) {
  return useMutation({
    mutationFn: (formData: FormData) =>
      publicRequest<ApplySuccess>(`/public/apply/${slug}`, {
        method: "POST",
        body: formData,
      }),
  });
}
