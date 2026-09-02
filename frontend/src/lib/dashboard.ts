import { useQuery } from "@tanstack/react-query";
import { api } from "./http";
import type { components } from "./api";

export type DashboardStats = components["schemas"]["DashboardStatsOut"];

/** "Real-time" here means periodic refetch, not a websocket — nothing else
 * in this codebase has push infra, and a 30s poll is indistinguishable from
 * live for a recruiter glancing at counts. */
export function useDashboardStats() {
  return useQuery<DashboardStats>({
    queryKey: ["dashboard", "stats"],
    queryFn: () => api.get<DashboardStats>("/dashboard/stats"),
    refetchInterval: 30_000,
  });
}

/** Top N non-zero entries, for a KPI card's small breakdown chips — highest
 * count first, ties broken by insertion order (the enum's declared order). */
export function topEntries<K extends string>(
  record: Record<K, number>,
  n = 2,
): [K, number][] {
  return (Object.entries(record) as [K, number][])
    .filter(([, count]) => count > 0)
    .sort((a, b) => b[1] - a[1])
    .slice(0, n);
}
