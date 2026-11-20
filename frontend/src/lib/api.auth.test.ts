import { beforeEach, describe, expect, it, vi } from "vitest";
import { getExams, login, setUnauthorizedHandler } from "./api";

const jsonResponse = (body: unknown, status: number) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });

describe("global 401 handling", () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
    setUnauthorizedHandler(null);
  });

  it("keeps the session when a stray 401 is contradicted by /auth/me", async () => {
    const handler = vi.fn();
    setUnauthorizedHandler(handler);
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ detail: "Not authenticated" }, 401))
      .mockResolvedValueOnce(jsonResponse({ email: "u@example.com" }, 200));
    vi.stubGlobal("fetch", fetchMock);

    await expect(getExams()).rejects.toThrow(/Not authenticated/);
    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(String(fetchMock.mock.calls[1][0])).toContain("/auth/me");
    expect(handler).not.toHaveBeenCalled();
  });

  it("clears the session when /auth/me also returns 401", async () => {
    const handler = vi.fn();
    setUnauthorizedHandler(handler);
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ detail: "Not authenticated" }, 401)));

    await expect(getExams()).rejects.toThrow(/Not authenticated/);
    await vi.waitFor(() => expect(handler).toHaveBeenCalledTimes(1));
  });

  it("does not clear the session on a failed login (bad credentials)", async () => {
    const handler = vi.fn();
    setUnauthorizedHandler(handler);
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ detail: "Invalid email or password" }, 401))
      .mockResolvedValueOnce(jsonResponse({ email: "u@example.com" }, 200));
    vi.stubGlobal("fetch", fetchMock);

    await expect(login("u@example.com", "wrong")).rejects.toThrow(
      /Invalid email or password/,
    );
    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(handler).not.toHaveBeenCalled();
  });
});
