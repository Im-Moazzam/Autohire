import { useQuery } from "@tanstack/react-query";
import { api, API_URL, ApiError } from "./http";
import type { components } from "./api";

export type Recruiter = components["schemas"]["RecruiterOut"];

/** Full-page navigation — this is a browser redirect chain (login -> Google
 * consent -> callback), not an API call, so it must not go through fetch(). */
export const googleLoginUrl = `${API_URL}/auth/google/login`;

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
