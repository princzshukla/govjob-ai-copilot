// src/hooks/use-me.ts
import { useQuery } from "@tanstack/react-query";
import * as api from "@/lib/govjob/api";

/**
 * The session user, fetched in the browser only (never during SSR).
 * Guests resolve to `null` instead of throwing.
 */
export function useMe() {
  return useQuery({
    queryKey: ["me"],
    queryFn: () => api.getMe(),
    staleTime: 5 * 60 * 1000,
    retry: false,
    enabled: typeof window !== "undefined",
  });
}
