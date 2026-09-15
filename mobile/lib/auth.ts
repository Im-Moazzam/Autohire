import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { components } from "./api";
import { api, ApiError } from "./http";

export type Recruiter = components["schemas"]["RecruiterOut"];

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

/** Same endpoint the web app calls — the response's Set-Cookie header
 * clears the session cookie in whichever cookie jar handled the request
 * (the bridge WebView's, on native; the browser's, on web). No local
 * cookie value to clear ourselves either way. */
export function useLogout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<void>("/auth/logout"),
    onSuccess: () => queryClient.setQueryData(["auth", "me"], null),
  });
}
