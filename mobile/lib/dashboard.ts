import { useQuery } from "@tanstack/react-query";
import type { components } from "./api";
import { api } from "./http";

export type DashboardStats = components["schemas"]["DashboardStatsOut"];

export function useDashboardStats() {
  return useQuery<DashboardStats>({
    queryKey: ["dashboard", "stats"],
    queryFn: () => api.get<DashboardStats>("/dashboard/stats"),
    refetchInterval: 30_000,
  });
}

export function topEntries<K extends string>(
  record: Record<K, number>,
  n = 3,
): [K, number][] {
  return (Object.entries(record) as [K, number][])
    .filter(([, count]) => count > 0)
    .sort((a, b) => b[1] - a[1])
    .slice(0, n);
}
