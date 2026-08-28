import { useQuery } from "@tanstack/react-query";
import { api } from "./http";
import type { components } from "./api";

export type Task = components["schemas"]["TaskOut"];

const TERMINAL: Task["status"][] = ["SUCCESS", "FAILED", "RETRIED"];

/** Polls a background task (rank/parse/schedule) until it reaches a terminal status. */
export function useTask(taskId: string | undefined) {
  return useQuery<Task>({
    queryKey: ["tasks", taskId],
    queryFn: () => api.get<Task>(`/tasks/${taskId}`),
    enabled: !!taskId,
    refetchInterval: (query) =>
      query.state.data && TERMINAL.includes(query.state.data.status)
        ? false
        : 1500,
  });
}
