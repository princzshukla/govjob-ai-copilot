// src/lib/govjob/use-mastery.ts
import { useQuery } from "@tanstack/react-query";
import { fetchUserMastery } from "@/lib/govjob/api";
import type { UserMasteryResponse, TopicMasteryItem } from "@/types/govjob";

// Re-export so components importing from use-mastery still work seamlessly
export type { TopicMasteryItem, UserMasteryResponse as MasteryResponse };

export function useTopicMastery(
  userId: string = "usr_demo_001",
  examId: string = "ssc-cgl-tier1"
) {
  return useQuery<UserMasteryResponse, Error>({
    queryKey: ["topic-mastery", userId, examId],
    queryFn: () => fetchUserMastery(userId, examId),
    staleTime: 1000 * 60 * 2, // 2 minutes
  });
}