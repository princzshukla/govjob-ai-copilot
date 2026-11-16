/**
 * Guest-side persistence in sessionStorage.
 *
 * - the profile draft survives tab switches AND page reloads within the tab
 * - the last eligibility result is cached so feed cards keep their verdicts
 * Both are cleared on sign-out / delete-account (they are personal data).
 */

import type { CandidateProfile, EligibilityCheckResponse } from "../types";

const PROFILE_KEY = "rozgar:guest-profile";
const ELIGIBILITY_KEY = "rozgar:eligibility-result";

function read<T>(key: string): T | null {
  try {
    const raw = sessionStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : null;
  } catch {
    return null;
  }
}

function write(key: string, value: unknown): void {
  try {
    sessionStorage.setItem(key, JSON.stringify(value));
  } catch {
    // storage full — non-fatal
  }
}

export const loadDraftProfile = (): CandidateProfile | null => read(PROFILE_KEY);
export const saveDraftProfile = (p: CandidateProfile): void => write(PROFILE_KEY, p);
export const clearDraftProfile = (): void => {
  try {
    sessionStorage.removeItem(PROFILE_KEY);
  } catch {
    /* ignore */
  }
};

export const loadEligibilityResult = (): EligibilityCheckResponse | null =>
  read(ELIGIBILITY_KEY);
export const saveEligibilityResult = (r: EligibilityCheckResponse): void =>
  write(ELIGIBILITY_KEY, r);
export const clearEligibilityResult = (): void => {
  try {
    sessionStorage.removeItem(ELIGIBILITY_KEY);
  } catch {
    /* ignore */
  }
};

export function clearSessionUserData(): void {
  clearDraftProfile();
  clearEligibilityResult();
}
