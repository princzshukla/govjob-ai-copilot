// src/stores/govjob-store.ts
import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";
import type { CandidateProfile } from "@/types/govjob";

/**
 * Guest draft + small, ephemeral UI flags.
 *
 * Anything persisted to sessionStorage is explicitly whitelisted: the parsed
 * profile fields only. Raw resume text, file contents and auth tokens are
 * never stored here (or anywhere else in the web app).
 */
interface GovJobState {
  /** The guest's parsed/manual profile draft. Persisted to sessionStorage. */
  draftProfile: CandidateProfile | null;
  /** True when an API call returned 401; the sign-in dialog consumes this. */
  signInRequested: boolean;
  setDraftProfile: (profile: CandidateProfile) => void;
  clearDraftProfile: () => void;
  requestSignIn: () => void;
  closeSignIn: () => void;
}

export const useGovJobStore = create<GovJobState>()(
  persist(
    (set) => ({
      draftProfile: null,
      signInRequested: false,
      setDraftProfile: (draftProfile) => set({ draftProfile }),
      clearDraftProfile: () => set({ draftProfile: null }),
      requestSignIn: () => set({ signInRequested: true }),
      closeSignIn: () => set({ signInRequested: false }),
    }),
    {
      name: "govjob-draft",
      storage: createJSONStorage(() => sessionStorage),
      // Only the guest draft survives a page reload; UI flags are ephemeral.
      partialize: (state) => ({ draftProfile: state.draftProfile }),
    },
  ),
);

export function getDraftProfile(): CandidateProfile | null {
  return useGovJobStore.getState().draftProfile;
}
