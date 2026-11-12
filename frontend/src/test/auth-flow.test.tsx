import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, renderHook, screen } from "@testing-library/react";
import { act } from "react";

import { useAuth } from "@/hooks/use-auth";
import { AuthDialog } from "@/components/auth/auth-dialog";
import { useGovJobStore } from "@/stores/govjob-store";

// Mock the whole API layer; we test orchestration, not HTTP.
vi.mock("@/lib/govjob/api", () => {
  const user = {
    id: 7,
    email: "audit@example.com",
    full_name: "Audit User",
    phone: null,
    created_at: "2026-01-01T00:00:00Z",
  };
  return {
    getMe: vi.fn(async () => null),
    login: vi.fn(async () => user),
    register: vi.fn(async () => user),
    logout: vi.fn(async () => {
      // Even a broken network must not strand the user signed in locally.
      throw new Error("network down");
    }),
    deleteAccount: vi.fn(async () => undefined),
    claimMyDraft: vi.fn(async () => ({
      status: "claimed" as const,
      profile: { id: "p1" },
    })),
  };
});
import * as api from "@/lib/govjob/api";

function makeWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 }, mutations: { retry: false } },
  });
  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
  return { queryClient, wrapper };
}

beforeEach(() => {
  window.sessionStorage.clear();
  useGovJobStore.getState().clearDraftProfile();
  useGovJobStore.getState().closeSignIn();
  vi.clearAllMocks();
});

describe("useAuth sign-in flow", () => {
  it("claims the guest draft exactly once, then clears it", async () => {
    useGovJobStore.getState().setDraftProfile({ full_name: "Guest Draft User" });
    const { wrapper } = makeWrapper();
    const { result } = renderHook(() => useAuth(), { wrapper });

    await act(async () => {
      await result.current.signIn("audit@example.com", "secret-password");
    });

    expect(api.login).toHaveBeenCalledWith("audit@example.com", "secret-password");
    expect(api.claimMyDraft).toHaveBeenCalledTimes(1);
    expect(api.claimMyDraft).toHaveBeenCalledWith({ full_name: "Guest Draft User" });
    expect(useGovJobStore.getState().draftProfile).toBeNull();
  });

  it("keeps the draft when claim-draft fails, so nothing is lost", async () => {
    vi.mocked(api.claimMyDraft).mockRejectedValueOnce(new Error("server down"));
    useGovJobStore.getState().setDraftProfile({ full_name: "Guest Draft User" });
    const { wrapper } = makeWrapper();
    const { result } = renderHook(() => useAuth(), { wrapper });

    await act(async () => {
      await result.current.signIn("audit@example.com", "secret-password");
    });

    expect(api.claimMyDraft).toHaveBeenCalledTimes(1);
    // Draft is preserved for a later retry instead of being silently dropped.
    expect(useGovJobStore.getState().draftProfile).not.toBeNull();
  });

  it("clears local state and does not throw when logout hits a broken network", async () => {
    useGovJobStore.getState().setDraftProfile({ full_name: "Guest" });
    useGovJobStore.getState().requestSignIn();
    const { wrapper, queryClient } = makeWrapper();
    const { result } = renderHook(() => useAuth(), { wrapper });

    await act(async () => {
      await result.current.signOut();
    });

    expect(api.logout).toHaveBeenCalledTimes(1);
    expect(useGovJobStore.getState().draftProfile).toBeNull();
    expect(useGovJobStore.getState().signInRequested).toBe(false);
    expect(queryClient.getQueryCache().getAll()).toHaveLength(0);
  });
});

describe("AuthDialog", () => {
  it("renders nothing until the store requests sign-in", () => {
    const { wrapper } = makeWrapper();
    render(<AuthDialog />, { wrapper });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("opens on the sign-in tab when a save point requests sign-in", () => {
    useGovJobStore.getState().requestSignIn();
    const { wrapper } = makeWrapper();
    render(<AuthDialog />, { wrapper });

    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("Sign in to GovJob Copilot")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sign in" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Create account" })).toBeInTheDocument();
  });
});
