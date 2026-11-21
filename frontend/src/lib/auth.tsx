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
  /** Whether the backend has Google sign-in configured. */
  googleEnabled: boolean;
  /** Post-first-Google-login phone step. */
  phoneSetupOpen: boolean;
  closePhoneSetup: () => void;
  savePhone: (phone: string) => Promise<void>;
}

const AUTH_ERRORS: Record<string, { title: string; detail: string }> = {
  account_exists: {
    title: "Account already exists",
    detail: "An account with this email exists. Sign in with your password first.",
  },
  expired_state: { title: "Sign-in expired", detail: "Please try Google sign-in again." },
  state_mismatch: { title: "Could not verify", detail: "Please try Google sign-in again." },
  bad_nonce: { title: "Could not verify", detail: "Please try Google sign-in again." },
  unverified_email: {
    title: "Email not verified",
    detail: "Use a Google account with a verified email address.",
  },
  google_verification_failed: { title: "Sign-in failed", detail: "Please try again." },
  google_cancelled: { title: "Cancelled", detail: "Google sign-in was cancelled." },
  google_invalid_request: { title: "Sign-in failed", detail: "Please try again." },
};

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
  const [googleEnabled, setGoogleEnabled] = useState(false);
  const [phoneSetupOpen, setPhoneSetupOpen] = useState(false);

  const promptSignIn = useCallback((mode: AuthModalMode = "login") => {
    setAuthModalMode(mode);
    setAuthModalOpen(true);
  }, []);
  const closeAuthModal = useCallback(() => setAuthModalOpen(false), []);
  const closePhoneSetup = useCallback(() => setPhoneSetupOpen(false), []);
  const savePhone = useCallback(async (phone: string) => {
    const updated = await api.updatePhone(phone);
    setUser(updated);
    setPhoneSetupOpen(false);
    toast("success", "Profile complete", "Your mobile number was saved.");
  }, []);

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

  // Show Google only when the backend is configured for it.
  useEffect(() => {
    let cancelled = false;
    api.getAuthProviders().then((p) => {
      if (!cancelled) setGoogleEnabled(p.google);
    }).catch(() => { /* guest-facing feature; never block the app */ });
    return () => { cancelled = true; };
  }, []);

  // The Google callback redirects here with short markers (never tokens).
  useEffect(() => {
    const url = new URL(window.location.href);
    if (!url.searchParams.has("auth_error") && url.searchParams.get("profile") !== "phone") return;

    const code = url.searchParams.get("auth_error");
    const message = code ? AUTH_ERRORS[code] : null;
    if (message) toast("warn", message.title, message.detail);
    if (url.searchParams.get("profile") === "phone") setPhoneSetupOpen(true);

    url.searchParams.delete("auth_error");
    url.searchParams.delete("profile");
    window.history.replaceState({}, "", url.pathname + url.search + url.hash);
  }, []);

  const signIn = useCallback(async (email: string, password: string) => {
    const u = await api.login(email, password);
    // Publish the session first: a failed draft claim must never clear the
    // freshly established user (the global 401 handler can run during it).
    setUser(u);
    await claimGuestDraft();
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
      setUser(u);
      await claimGuestDraft();
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
      googleEnabled,
      phoneSetupOpen,
      closePhoneSetup,
      savePhone,
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
      googleEnabled,
      phoneSetupOpen,
      closePhoneSetup,
      savePhone,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
