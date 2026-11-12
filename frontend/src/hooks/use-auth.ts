// src/hooks/use-auth.ts
import { useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import * as api from "@/lib/govjob/api";
import { useGovJobStore } from "@/stores/govjob-store";
import { useMe } from "./use-me";

export interface UseAuth {
  /** undefined while loading, null for guests, the user otherwise. */
  user: api.UserOut | null | undefined;
  isLoading: boolean;
  isAuthenticated: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (name: string, email: string, password: string, phone?: string) => Promise<void>;
  signOut: () => Promise<void>;
  /** Confirmed, destructive. Throws on wrong password ("Invalid password"). */
  removeAccount: (password: string) => Promise<void>;
}

/**
 * Session auth state and actions, backed by the ["me"] query (retry: false).
 * Signing in also claims the guest draft exactly once and only then clears it.
 */
export function useAuth(): UseAuth {
  const queryClient = useQueryClient();
  const { data: me, isLoading } = useMe();
  const user = me ?? null;

  const finishSignIn = useCallback(
    async (userOut: api.UserOut) => {
      // Claim the guest draft exactly once after a successful sign-in.
      const draft = useGovJobStore.getState().draftProfile;
      if (draft) {
        try {
          const resp = await api.claimMyDraft(draft);
          useGovJobStore.getState().clearDraftProfile();
          if (resp.status === "already_claimed") {
            toast.message("Your resume draft was already in your account.");
          } else {
            toast.success("Your resume draft is saved to your account.");
          }
        } catch {
          // Keep the draft locally — never lose the user's work silently.
          toast.error("Could not save your draft to your account — kept it locally.", {
            duration: 8000,
          });
        }
        queryClient.invalidateQueries({ queryKey: ["roadmap"] });
        queryClient.invalidateQueries({ queryKey: ["mastery"] });
        queryClient.invalidateQueries({ queryKey: ["profile"] });
      }
      // The response already carries the user; seed the cache, then refresh.
      queryClient.setQueryData(["me"], userOut);
      await queryClient.invalidateQueries({ queryKey: ["me"] });
    },
    [queryClient],
  );

  const signIn = useCallback(
    async (email: string, password: string) => {
      const userOut = await api.login(email, password);
      await finishSignIn(userOut);
    },
    [finishSignIn],
  );

  const signUp = useCallback(
    async (name: string, email: string, password: string, phone?: string) => {
      const userOut = await api.register({
        email,
        password,
        full_name: name,
        phone: phone?.trim() ? phone.trim() : null,
      });
      await finishSignIn(userOut);
    },
    [finishSignIn],
  );

  const resetLocalState = useCallback(() => {
    queryClient.clear();
    useGovJobStore.getState().clearDraftProfile();
    useGovJobStore.getState().closeSignIn();
  }, [queryClient]);

  const signOut = useCallback(async () => {
    try {
      await api.logout();
    } catch {
      // Signing out should never strand the user; clear local state regardless.
    }
    resetLocalState();
  }, [resetLocalState]);

  const removeAccount = useCallback(
    async (password: string) => {
      await api.deleteAccount(password);
      resetLocalState();
    },
    [resetLocalState],
  );

  return {
    user,
    isLoading,
    isAuthenticated: !!user,
    signIn,
    signUp,
    signOut,
    removeAccount,
  };
}
