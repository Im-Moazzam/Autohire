import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, API_URL, ApiError } from "./http";
import type { components } from "./api";

export type Recruiter = components["schemas"]["RecruiterOut"];

/** Full-page navigation — this is a browser redirect chain (login -> Google
 * consent -> callback), not an API call, so it must not go through fetch(). */
export const googleLoginUrl = `${API_URL}/auth/google/login`;

/** Same reasoning as googleLoginUrl — restarts consent and replaces the
 * stored tokens (US-03/TS-07). Linked from AppShell's REAUTH_REQUIRED banner. */
export const googleReconnectUrl = `${API_URL}/auth/google/reconnect`;

export function useCurrentRecruiter() {
  return useQuery<Recruiter | null>({
    queryKey: ["auth", "me"],
    queryFn: async () => {
      try {
        return await api.get<Recruiter>("/auth/me");
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) return null;
        throw err;
      }
    },
  });
}

export function useLogout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<void>("/auth/logout"),
    onSuccess: () => queryClient.setQueryData(["auth", "me"], null),
  });
}
