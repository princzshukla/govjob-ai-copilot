// src/hooks/use-roadmap.ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as api from "@/lib/govjob/api";
import type { SavedRoadmap } from "@/types/govjob";
import { useMe } from "./use-me";

export function roadmapKey(ownerId: number | "guest", examId: string) {
  return ["roadmap", ownerId, examId] as const;
}

export function useRoadmapQuery(examId: string | null | undefined) {
  const { data: me } = useMe();
  const ownerId = me?.id ?? "guest";

  return useQuery({
    queryKey: roadmapKey(ownerId, examId ?? "unknown-exam"),
    queryFn: () => api.getMyRoadmap(examId as string),
    enabled: me?.id != null && !!examId,
    staleTime: 60 * 1000,
    retry: false,
  });
}

/**
 * Toggle a week done/undone. Optimistic: flips the cached roadmap UI
 * instantly and rolls back if the server rejects the change (e.g. week
 * out of range, or the roadmap no longer belongs to this session).
 */
export function useToggleRoadmapWeek(examId: string) {
  const queryClient = useQueryClient();
  const { data: me } = useMe();
  const ownerId = me?.id ?? "guest";
  const queryKey = roadmapKey(ownerId, examId);

  return useMutation({
    mutationFn: ({ roadmapId, weekNo, done }: { roadmapId: string; weekNo: number; done: boolean }) =>
      api.toggleRoadmapWeek(roadmapId, weekNo, done),

    onMutate: async ({ weekNo, done }) => {
      await queryClient.cancelQueries({ queryKey });
      const previous = queryClient.getQueryData<SavedRoadmap | null>(queryKey) ?? null;
      if (!previous) return { previous };

      const doneSet = new Set(previous.completed_weeks);
      if (done) doneSet.add(weekNo);
      else doneSet.delete(weekNo);
      const completedWeeks = [...doneSet].sort((a, b) => a - b);
      const targetWeeks = previous.target_weeks || 1;

      queryClient.setQueryData<SavedRoadmap>(queryKey, {
        ...previous,
        completed_weeks: completedWeeks,
        completed_count: completedWeeks.length,
        percent: Math.round((100 * completedWeeks.length) / targetWeeks),
      });
      return { previous };
    },

    onError: (_error, _vars, context) => {
      if (context && context.previous !== undefined) {
        queryClient.setQueryData(queryKey, context.previous);
      }
    },

    onSettled: () => {
      queryClient.invalidateQueries({ queryKey });
    },
  });
}
