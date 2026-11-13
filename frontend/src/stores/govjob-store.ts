// src/stores/govjob-store.ts
import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";
import type {
  CandidateProfile,
  MissingFieldPrompt,
  EligibilityCheckResponse,
} from "@/types/govjob";

/**
 * Guest draft + small UI state.
 *
 * Anything persisted to sessionStorage is explicitly whitelisted in
 * `partialize`: the parsed profile and its derived UI (missing-field prompts,
 * parse message, latest eligibility check and the roadmap length preference).
 * Raw resume text, file contents and auth tokens are never stored here (or
 * anywhere else in the web app).
 *
 * The same whitelist is what lets the main app survive in-app route changes:
 * navigating / → /account unmounts the app component, so this store is the
 * single source of truth for anything that must not reset.
 */
interface GovJobState {
  /** The guest's parsed/manual profile draft. Persisted to sessionStorage. */
  draftProfile: CandidateProfile | null;
  /** True when an API call returned 401; the sign-in dialog consumes this. */
  signInRequested: boolean;
  /** Latest eligibility check result, derived from the profile draft. */
  eligibility: EligibilityCheckResponse | null;
  /** "Missing details" prompts from the resume parser. */
  missingFields: MissingFieldPrompt[];
  /** Informational banner text returned by the parser. */
  statusMessage: string;
  /** Week preference for roadmap generation. */
  targetWeeks: number;
  setDraftProfile: (profile: CandidateProfile) => void;
  clearDraftProfile: () => void;
  requestSignIn: () => void;
  closeSignIn: () => void;
  setEligibility: (eligibility: EligibilityCheckResponse | null) => void;
  setMissingFields: (missingFields: MissingFieldPrompt[]) => void;
  setStatusMessage: (statusMessage: string) => void;
  setTargetWeeks: (targetWeeks: number) => void;
  /** Drops resume-derived UI state (used on sign-out / account deletion). */
  clearSessionUi: () => void;
}

export const useGovJobStore = create<GovJobState>()(
  persist(
    (set) => ({
      draftProfile: null,
      signInRequested: false,
      eligibility: null,
      missingFields: [],
      statusMessage: "",
      targetWeeks: 12,
      setDraftProfile: (draftProfile) => set({ draftProfile }),
      clearDraftProfile: () => set({ draftProfile: null }),
      requestSignIn: () => set({ signInRequested: true }),
      closeSignIn: () => set({ signInRequested: false }),
      setEligibility: (eligibility) => set({ eligibility }),
      setMissingFields: (missingFields) => set({ missingFields }),
      setStatusMessage: (statusMessage) => set({ statusMessage }),
      setTargetWeeks: (targetWeeks) => set({ targetWeeks }),
      clearSessionUi: () =>
        set({
          eligibility: null,
          missingFields: [],
          statusMessage: "",
          targetWeeks: 12,
        }),
    }),
    {
      name: "govjob-draft",
      storage: createJSONStorage(() => sessionStorage),
      // Whitelisted UI state survives reloads; UI-only flags never persist.
      partialize: (state) => ({
        draftProfile: state.draftProfile,
        eligibility: state.eligibility,
        missingFields: state.missingFields,
        statusMessage: state.statusMessage,
        targetWeeks: state.targetWeeks,
      }),
    },
  ),
);

export function getDraftProfile(): CandidateProfile | null {
  return useGovJobStore.getState().draftProfile;
}
