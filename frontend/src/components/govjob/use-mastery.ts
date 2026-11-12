// src/lib/govjob/use-mastery.ts
import { useQuery } from "@tanstack/react-query";
import { fetchUserMastery } from "@/lib/govjob/api";
import type { UserMasteryResponse, TopicMasteryItem } from "@/types/govjob";

// Re-export so components importing from use-mastery still work seamlessly
export type { TopicMasteryItem, UserMasteryResponse as MasteryResponse };

export function useTopicMastery(examId: string = "ssc-cgl-tier1") {
  return useQuery<UserMasteryResponse, Error>({
    // Mastery is always the session user's; no user id in the key or URL.
    queryKey: ["topic-mastery", examId],
    queryFn: () => fetchUserMastery(examId),
    staleTime: 1000 * 60 * 2, // 2 minutes
    // Guests get 401 by design; do not hammer the endpoint while signed out.
    retry: false,
  });
}
