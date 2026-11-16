/**
 * Minimal API client for the GovJob backend.
 * Session auth is an HttpOnly cookie — cross-origin calls must send credentials.
 */

// Both names are read so the app works with either the value written by setup.sh
// or a manually configured frontend/.env.
const API_BASE =
  import.meta.env["VITE_API_BASE_URL"] ??
  import.meta.env["VITE_GOVJOB_API_BASE"] ??
  "http://localhost:8000/api/v1";

const REQUEST_TIMEOUT_MS = 25_000;

const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;

// FastAPI returns `detail` as a string for HTTPException but as a LIST of
// validation-error objects for 422s. Coerce either into human text.
export function detailToMessage(detail: unknown, fallback: string): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const parts = detail
      .map((entry) => {
        if (!entry || typeof entry !== "object") return null;
        const loc = Array.isArray((entry as { loc?: unknown }).loc)
          ? ((entry as { loc: unknown[] }).loc as unknown[])
              .slice(1)
              .map((p) => String(p))
              .join(".")
          : "";
        const msg =
          typeof (entry as { msg?: unknown }).msg === "string"
            ? (entry as { msg: string }).msg
            : "Invalid value";
        return loc ? `${loc}: ${msg}` : msg;
      })
      .filter((s): s is string => !!s);
    return parts.length > 0 ? parts.join(". ") : fallback;
  }
  return fallback;
}

/** Coerces a date-ish value to YYYY-MM-DD, or null when it is unusable. */
export function toIsoDate(value: unknown): string | null {
  if (typeof value !== "string" || !value.trim()) return null;
  const trimmed = value.trim();
  if (ISO_DATE.test(trimmed)) return trimmed;
  const parsed = new Date(trimmed);
  if (Number.isNaN(parsed.getTime())) return null;
  return parsed.toISOString().slice(0, 10);
}

// Global 401 handler: registered once by the app so ANY API call answered with
// 401 flips the UI to signed-out state.
type UnauthorizedHandler = () => void;
let unauthorizedHandler: UnauthorizedHandler | null = null;

export function setUnauthorizedHandler(handler: UnauthorizedHandler | null): void {
  unauthorizedHandler = handler;
}

async function fetchWithTimeout(input: string, init?: RequestInit): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    return await fetch(input, {
      ...init,
      credentials: "include", // session cookie rides along cross-origin
      signal: controller.signal,
    });
  } finally {
    clearTimeout(timer);
  }
}

async function callApi<T>(path: string, init?: RequestInit): Promise<T> {
  try {
    const res = await fetchWithTimeout(`${API_BASE}${path}`, init);
    if (res.status === 401) {
      unauthorizedHandler?.();
      throw new Error("Not authenticated. Please sign in.");
    }
    if (!res.ok) {
      const body: unknown = await res.json().catch(() => ({}));
      throw new Error(
        detailToMessage(
          (body as { detail?: unknown }).detail,
          `Server returned HTTP ${res.status}: ${res.statusText}`,
        ),
      );
    }
    // 204 No Content must not be parsed as JSON.
    return (res.status === 204 ? undefined : await res.json()) as T;
  } catch (err) {
    if (err instanceof Error) {
      if (err.name === "AbortError") {
        throw new Error("Request timed out — is the backend running?");
      }
      throw err;
    }
    throw new Error("Failed to communicate with the backend.");
  }
}

// ==========================================
// Exams (the feed)
// ==========================================

import type { ExamsListResponse } from "../types";

export function getExams(): Promise<ExamsListResponse> {
  return callApi<ExamsListResponse>("/eligibility/exams");
}

export { API_BASE };
