import { beforeEach, describe, expect, it, vi } from "vitest";

import { indexSearchSchema } from "@/lib/search";
import * as api from "@/lib/govjob/api";
import { useGovJobStore } from "@/stores/govjob-store";

describe("index search params", () => {
  it("defaults the tab, exam and week", () => {
    expect(indexSearchSchema.parse({})).toEqual({
      tab: "profile",
      exam: "ssc-cgl-general",
      week: 1,
    });
  });

  it("coerces the week from the query string", () => {
    expect(indexSearchSchema.parse({ tab: "roadmap", exam: "ssc-cgl-tier1", week: "3" })).toEqual({
      tab: "roadmap",
      exam: "ssc-cgl-tier1",
      week: 3,
    });
  });

  it("falls back to safe defaults for garbage input", () => {
    expect(
      indexSearchSchema.parse({ tab: "nope", exam: "", week: 99 }),
    ).toEqual({ tab: "profile", exam: "ssc-cgl-general", week: 1 });
  });
});

describe("guest draft store", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
    useGovJobStore.getState().clearDraftProfile();
    useGovJobStore.getState().closeSignIn();
  });

  it("persists only the draft, never the sign-in flag", () => {
    useGovJobStore.getState().setDraftProfile({ full_name: "Guest User" });
    useGovJobStore.getState().requestSignIn();

    const raw = window.sessionStorage.getItem("govjob-draft");
    expect(raw).not.toBeNull();
    const persisted = JSON.parse(raw as string) as { state: Record<string, unknown> };

    expect(persisted.state).toMatchObject({
      draftProfile: { full_name: "Guest User" },
    });
    expect(persisted.state).not.toHaveProperty("signInRequested");
    expect(raw).not.toContain("raw_resume");
  });

  it("clears the draft when asked to", () => {
    useGovJobStore.getState().setDraftProfile({ full_name: "Guest User" });
    useGovJobStore.getState().clearDraftProfile();

    expect(useGovJobStore.getState().draftProfile).toBeNull();
  });
});

describe("global 401 handler", () => {
  beforeEach(() => {
    api.setUnauthorizedHandler(null);
    vi.restoreAllMocks();
  });

  it("getMe returns null for guests without invoking the 401 handler", async () => {
    const handler = vi.fn();
    api.setUnauthorizedHandler(handler);

    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(JSON.stringify({ detail: "Not authenticated" }), {
          status: 401,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );

    await expect(api.getMe()).resolves.toBeNull();
    expect(handler).not.toHaveBeenCalled();
  });

  it("invokes the handler when an authenticated call comes back 401", async () => {
    const handler = vi.fn();
    api.setUnauthorizedHandler(handler);

    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(JSON.stringify({ detail: "Not authenticated" }), {
          status: 401,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );

    await expect(api.getMyProfile()).rejects.toThrow();
    expect(handler).toHaveBeenCalledTimes(1);
  });
});
