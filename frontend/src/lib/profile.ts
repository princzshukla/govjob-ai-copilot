import type { CandidateProfile } from "../types";

/**
 * Defaults that the eligibility form displays. They must live in state, not
 * only in the rendered `<select>`: buildCandidatePayload() rejects a profile
 * whose category is missing, so a display-only fallback makes "Check
 * eligibility" fail even though the UI appears to show a selection.
 *
 * Category affects age relaxation and cut-offs, so General is an assumption
 * the user can see and change — never a silent guess by the resume parser.
 */
export const DEFAULT_CATEGORY = "General";
export const DEFAULT_GENDER = "Male";

/** A profile whose form defaults are real values, not display-only fallbacks. */
export interface NormalizedProfile extends CandidateProfile {
  category: string;
  gender: string;
}

function present(value: string | null | undefined): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

export function withProfileDefaults(profile: CandidateProfile): NormalizedProfile {
  return {
    ...profile,
    category: present(profile.category) ? profile.category : DEFAULT_CATEGORY,
    gender: present(profile.gender) ? profile.gender : DEFAULT_GENDER,
  };
}
