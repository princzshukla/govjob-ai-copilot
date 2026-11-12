import { z } from "zod";

export const indexSearchSchema = z.object({
  tab: z
    .enum(["profile", "eligibility", "roadmap", "documents", "adaptive"])
    .catch("profile"),
  exam: z.string().min(1).max(64).catch("ssc-cgl-general"),
  week: z.coerce.number().int().min(1).max(52).catch(1),
});

export type IndexSearch = z.infer<typeof indexSearchSchema>;
