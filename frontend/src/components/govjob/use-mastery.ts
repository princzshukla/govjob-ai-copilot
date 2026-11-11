// src/lib/govjob/use-mastery.ts
import { useQuery } from "@tanstack/react-query";

export interface TopicMasteryItem {
  topic: string;
  subject: string;
  accuracy_ema: number;
  attempts_count: number;
  status: "Mastered" | "Moderate" | "Needs Revision";
  last_reviewed_at: string;
}

export interface MasteryResponse {
  user_id: string;
  exam_id: string;
  topics: TopicMasteryItem[];
}

const API_BASE = "http://127.0.0.1:8000/api/v1/adaptive";

export function useTopicMastery(userId: string = "usr_demo_001", examId: string = "ssc-cgl-tier1") {
  return useQuery<MasteryResponse>({
    queryKey: ["topic-mastery", userId, examId],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/mastery/${encodeURIComponent(userId)}/${encodeURIComponent(examId)}`);
      if (!res.ok) {
        throw new Error("Failed to fetch mastery status");
      }
      return res.json();
    },
    staleTime: 1000 * 60 * 2, // 2 minutes
  });
}