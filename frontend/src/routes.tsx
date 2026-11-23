/**
 * Public URL map for the site.
 *
 * Phase 1: real paths instead of `?tab=` query strings. The old `?tab=` values
 * are kept only so old links can be forwarded with <Navigate replace>.
 */
export const TABS = [
  { label: "Latest Jobs", param: "jobs", path: "/" },
  { label: "Admit Cards", param: "admit", path: "/admit-cards" },
  { label: "My Eligibility", param: "eligibility", path: "/eligibility" },
  { label: "My Roadmap", param: "roadmap", path: "/roadmap" },
  {
    label: "Photo & Signature",
    param: "documents",
    path: "/tools/photo-signature-resizer",
  },
] as const;

export type Tab = (typeof TABS)[number]["label"];

export const PATH_FOR_TAB: Record<Tab, string> = {
  "Latest Jobs": "/",
  "Admit Cards": "/admit-cards",
  "My Eligibility": "/eligibility",
  "My Roadmap": "/roadmap",
  "Photo & Signature": "/tools/photo-signature-resizer",
};

const LEGACY_PARAM_TO_TAB: Record<string, Tab> = {
  jobs: "Latest Jobs",
  admit: "Admit Cards",
  eligibility: "My Eligibility",
  roadmap: "My Roadmap",
  documents: "Photo & Signature",
  // common typo in shared links
  document: "Photo & Signature",
};

/** Map an old `?tab=` value to its new path. Returns null when absent/unknown. */
export function tabFromLegacyParam(param: string | null): Tab | null {
  if (!param) return null;
  return LEGACY_PARAM_TO_TAB[param] ?? null;
}
