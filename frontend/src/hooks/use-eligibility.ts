// src/hooks/use-eligibility.ts
import { useMutation } from "@tanstack/react-query";
import * as api from "@/lib/govjob/api";
import type { CandidateProfile } from "@/types/govjob";

/**
 * The eligibility POST is a side-effecting check (per-IP rate-limited on the
 * backend), not a cache entry: model it as a mutation and read `.data` for
 * the latest response.
 */
export function useEligibilityCheck() {
  return useMutation({
    mutationFn: ({ profile, examId }: { profile: CandidateProfile; examId: string }) =>
      api.checkEligibility(profile, examId),
  });
}
