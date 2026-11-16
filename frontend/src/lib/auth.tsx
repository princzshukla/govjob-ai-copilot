/**
 * Session-user context for the Rozgar frontend.
 *
 * One source of truth for: who is signed in, signing in/out, deleting the
 * account, and opening the auth modal from anywhere (e.g. a guest clicking
 * "Save to my account" on the eligibility page).
 *
 * Any API 401 registered via setUnauthorizedHandler drops the local user so
 * the masthead flips back to Register/Login automatically.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import * as api from "./api";
import { toast } from "./toast";
import { clearSessionUserData, loadDraftProfile, clearDraftProfile } from "./draft";
import type { UserOut } from "../types";

export type AuthModalMode = "login" | "register";

export interface AuthContextValue {
  user: UserOut | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (name: string, email: string, password: string, phone?: string) => Promise<void>;
  signOut: () => Promise<void>;
  removeAccount: (password: string) => Promise<void>;
  /** Re-fetch /auth/me and replace the cached user. */
  refresh: () => Promise<void>;
  /** Open the auth modal in a given mode from anywhere in the tree. */
  promptSignIn: (mode?: AuthModalMode) => void;
  /** Modal state lives in the provider so any component can open it. */
  authModalOpen: boolean;
  authModalMode: AuthModalMode;
  closeAuthModal: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

async function claimGuestDraft(): Promise<void> {
  const draft = loadDraftProfile();
  if (!draft || Object.keys(draft).length === 0) return;
  try {
    const resp = await api.claimMyDraft(draft);
    clearDraftProfile();
    if (resp.status === "already_claimed") {
      toast("info", "Draft already in account", "Your saved profile was kept as-is.");
    } else {
      toast("success", "Draft saved to your account", "Your resume profile is attached.");
    }
  } catch {
    // Keep the draft locally — never lose the user's work silently.
    toast("warn", "Could not save draft", "It stays on this device — sign in again to retry.");
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [authModalMode, setAuthModalMode] = useState<AuthModalMode>("login");

  const promptSignIn = useCallback((mode: AuthModalMode = "login") => {
    setAuthModalMode(mode);
    setAuthModalOpen(true);
  }, []);
  const closeAuthModal = useCallback(() => setAuthModalOpen(false), []);

  const refresh = useCallback(async () => {
    try {
      setUser(await api.getMe());
    } catch {
      setUser(null);
    }
  }, []);

  // Any 401 anywhere in the app -> drop the local user; the masthead flips
  // back to signed-out state. Personal sessionStorage is wiped too.
  useEffect(() => {
    api.setUnauthorizedHandler(() => {
      setUser(null);
      clearSessionUserData();
    });
    return () => api.setUnauthorizedHandler(null);
  }, []);

  useEffect(() => {
    let cancelled = false;
    api
      .getMe()
      .then((u) => {
        if (!cancelled) {
          setUser(u);
          setLoading(false);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setUser(null);
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const signIn = useCallback(async (email: string, password: string) => {
    const u = await api.login(email, password);
    await claimGuestDraft();
    setUser(u);
    toast("success", "Signed in", `Welcome back${u.full_name ? `, ${u.full_name.split(" ")[0]}` : ""}.`);
  }, []);

  const signUp = useCallback(
    async (name: string, email: string, password: string, phone?: string) => {
      const u = await api.register({
        email,
        password,
        full_name: name,
        phone: phone?.replace(/\D/g, "") ? phone.replace(/\D/g, "") : null,
      });
      await claimGuestDraft();
      setUser(u);
      toast("success", "Account created", "Welcome aboard.");
    },
    [],
  );

  const signOut = useCallback(async () => {
    await api.logout(); // never throws
    setUser(null);
    clearSessionUserData();
    toast("info", "Signed out", "You are browsing as a guest.");
  }, []);

  const removeAccount = useCallback(async (password: string) => {
    await api.deleteAccount(password);
    setUser(null);
    clearSessionUserData();
    toast("info", "Account deleted", "Your data has been removed.");
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      signIn,
      signUp,
      signOut,
      removeAccount,
      refresh,
      promptSignIn,
      authModalOpen,
      authModalMode,
      closeAuthModal,
    }),
    [
      user,
      loading,
      signIn,
      signUp,
      signOut,
      removeAccount,
      refresh,
      promptSignIn,
      authModalOpen,
      authModalMode,
      closeAuthModal,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
