/**
 * Minimal API client for the GovJob backend.
 * Session auth is an HttpOnly cookie — cross-origin calls must send credentials.
 */

import type {
  CandidateProfile,
  ClaimDraftResponse,
  EligibilityCheckResponse,
  ExamsListResponse,
  ParseResumeResult,
  RoadmapProgress,
  SavedRoadmap,
  SaveProfileResponse,
  StudyRoadmapResponse,
  TelegramLinkStartResponse,
  TelegramLinkStatusResponse,
  UserMasteryResponse,
  UserOut,
  RegisterPayload,
} from "../types";

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

/**
 * Coerces a date-ish value to YYYY-MM-DD, or null when unusable.
 * Explicitly formats local Y/M/D — `toISOString()` would shift a day backwards
 * for IST users when the input was parsed as local midnight.
 */
export function toIsoDate(value: unknown): string | null {
  if (typeof value !== "string" || !value.trim()) return null;
  const trimmed = value.trim();
  if (ISO_DATE.test(trimmed)) return trimmed;

  const parsed = new Date(trimmed);
  if (Number.isNaN(parsed.getTime())) return null;
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${parsed.getFullYear()}-${pad(parsed.getMonth() + 1)}-${pad(parsed.getDate())}`;
}

function toBoolean(value: unknown): boolean {
  if (typeof value === "boolean") return value;
  if (typeof value === "string") {
    return ["yes", "true", "1"].includes(value.trim().toLowerCase());
  }
  return false;
}

function asTrimmedString(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

/**
 * Strict payload for the eligibility + persistence endpoints. Missing statutory
 * fields raise an error instead of being silently replaced with placeholders.
 */
export function buildCandidatePayload(
  profile: CandidateProfile,
): Record<string, unknown> {
  const raw = profile as Record<string, unknown>;
  const missing: string[] = [];

  const dob = toIsoDate(raw["dob"] ?? raw["date_of_birth"]);
  if (!dob) missing.push("Date of birth");

  const rawCategory = asTrimmedString(raw["category"]);
  const category = rawCategory === "OBC" ? "OBC-NCL" : rawCategory;
  if (!category) missing.push("Reservation category");

  const domicileState = asTrimmedString(raw["domicile_state"]);
  if (!domicileState) missing.push("Domicile state");

  const highestDegree = asTrimmedString(raw["highest_degree"]);
  if (!highestDegree) missing.push("Highest qualification");

  const rawPercentage = raw["percentage_cgpa"];
  const percentageValue =
    rawPercentage === null || rawPercentage === undefined || rawPercentage === ""
      ? Number.NaN
      : Number(rawPercentage);
  if (Number.isNaN(percentageValue)) missing.push("Graduation percentage");

  if (missing.length > 0) {
    throw new Error(
      `Please fill in the following before checking eligibility: ${missing.join(", ")}.`,
    );
  }

  const stream = asTrimmedString(raw["stream"]);
  const passingYear = raw["passing_year"];

  return {
    full_name: asTrimmedString(raw["full_name"]) || null,
    dob,
    gender: asTrimmedString(raw["gender"]) || "Male",
    category,
    is_pwd: toBoolean(raw["is_pwd"] ?? raw["physical_disability"]),
    domicile_state: domicileState,
    highest_degree: highestDegree,
    stream: stream || "Any",
    percentage_cgpa: percentageValue,
    passing_year: passingYear ? Number(passingYear) : null,
    skills: Array.isArray(raw["skills"]) ? raw["skills"] : [],
  };
}

/**
 * Best-effort payload for the claim-draft endpoint. Missing fields are simply
 * omitted — the server stores partial drafts instead of rejecting them.
 */
export function buildProfilePayload(
  profile: CandidateProfile,
): Record<string, unknown> {
  const raw = profile as Record<string, unknown>;
  const out: Record<string, unknown> = {};

  const fullName = asTrimmedString(raw["full_name"]);
  if (fullName) out["full_name"] = fullName;

  const dob = toIsoDate(raw["dob"] ?? raw["date_of_birth"]);
  if (dob) out["dob"] = dob;

  const gender = asTrimmedString(raw["gender"]);
  if (gender) out["gender"] = gender;

  const rawCategory = asTrimmedString(raw["category"]);
  if (rawCategory) out["category"] = rawCategory === "OBC" ? "OBC-NCL" : rawCategory;

  if (raw["is_pwd"] !== undefined || raw["physical_disability"] !== undefined) {
    out["is_pwd"] = toBoolean(raw["is_pwd"] ?? raw["physical_disability"]);
  }

  const domicileState = asTrimmedString(raw["domicile_state"]);
  if (domicileState) out["domicile_state"] = domicileState;

  const highestDegree = asTrimmedString(raw["highest_degree"]);
  if (highestDegree) out["highest_degree"] = highestDegree;

  const stream = asTrimmedString(raw["stream"]);
  if (stream) out["stream"] = stream;

  const rawPercentage = raw["percentage_cgpa"];
  if (rawPercentage !== null && rawPercentage !== undefined && rawPercentage !== "") {
    const parsed = Number(rawPercentage);
    if (!Number.isNaN(parsed)) out["percentage_cgpa"] = parsed;
  }

  if (
    raw["passing_year"] !== null &&
    raw["passing_year"] !== undefined &&
    raw["passing_year"] !== ""
  ) {
    const parsed = Number(raw["passing_year"]);
    if (Number.isFinite(parsed)) out["passing_year"] = parsed;
  }

  if (Array.isArray(raw["skills"])) {
    out["skills"] = raw["skills"].filter(
      (s): s is string => typeof s === "string" && !!s.trim(),
    );
  }

  return out;
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

/* ---------------- exams (the feed) ---------------- */

export function getExams(): Promise<ExamsListResponse> {
  return callApi<ExamsListResponse>("/eligibility/exams");
}

/* ---------------- auth ---------------- */

export function register(payload: RegisterPayload): Promise<UserOut> {
  return callApi<UserOut>("/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function login(email: string, password: string): Promise<UserOut> {
  return callApi<UserOut>("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
}

export async function logout(): Promise<void> {
  // Signing out should never strand the user; failure here still clears local state.
  await fetchWithTimeout(`${API_BASE}/auth/logout`, { method: "POST" }).catch(() => {});
}

/** Fetch the current session user. 401 (guest) returns null without raising. */
export async function getMe(): Promise<UserOut | null> {
  const res = await fetchWithTimeout(`${API_BASE}/auth/me`);
  if (res.status === 401) return null;
  if (!res.ok) throw new Error(`Could not load the session user (HTTP ${res.status})`);
  return (await res.json()) as UserOut;
}

/* ---------------- account ---------------- */

export function updateMyFullName(fullName: string): Promise<UserOut> {
  return callApi<UserOut>("/users/me", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ full_name: fullName }),
  });
}

export function changePassword(
  currentPassword: string,
  newPassword: string,
): Promise<{ message: string }> {
  return callApi<{ message: string }>("/users/me/change-password", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
  });
}

export async function deleteAccount(password: string): Promise<void> {
  const res = await fetchWithTimeout(`${API_BASE}/users/me`, {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password }),
  });
  if (res.status === 401) {
    unauthorizedHandler?.();
    throw new Error("Not authenticated. Please sign in.");
  }
  if (!res.ok) {
    const body: unknown = await res.json().catch(() => ({}));
    throw new Error(
      detailToMessage(
        (body as { detail?: unknown }).detail,
        `Could not delete account (HTTP ${res.status})`,
      ),
    );
  }
}

/* ---------------- profile draft + eligibility ---------------- */

export function claimMyDraft(profile: CandidateProfile): Promise<ClaimDraftResponse> {
  return callApi<ClaimDraftResponse>("/users/me/claim-draft", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(buildProfilePayload(profile)),
  });
}

export function parseResume(file: File): Promise<ParseResumeResult> {
  const formData = new FormData();
  formData.append("file", file);
  return callApi<ParseResumeResult>("/candidate/parse-resume", {
    method: "POST",
    body: formData,
  });
}

export function saveCandidateProfile(
  profile: CandidateProfile,
  existingProfileId?: string | null,
): Promise<SaveProfileResponse> {
  const payload = buildCandidatePayload(profile);
  const query = existingProfileId
    ? `?profile_id=${encodeURIComponent(existingProfileId)}`
    : "";
  return callApi<SaveProfileResponse>(`/candidate/profile${query}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function checkEligibility(
  profile: CandidateProfile,
  primaryExamId = "ssc-cgl-general",
): Promise<EligibilityCheckResponse> {
  const payload = buildCandidatePayload(profile);
  return callApi<EligibilityCheckResponse>(
    `/eligibility/check?primary_exam_id=${encodeURIComponent(primaryExamId)}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    },
  );
}

/* ---------------- roadmap + mastery ---------------- */

export function generateRoadmap(
  examId: string,
  targetWeeks: number,
): Promise<StudyRoadmapResponse> {
  return callApi<StudyRoadmapResponse>(
    `/eligibility/generate-roadmap/${encodeURIComponent(examId)}?target_weeks=${targetWeeks}`,
    { method: "POST" },
  );
}

export async function getMyRoadmap(examId: string): Promise<SavedRoadmap | null> {
  const res = await fetchWithTimeout(
    `${API_BASE}/users/me/roadmaps/${encodeURIComponent(examId)}`,
  );
  if (res.status === 401) {
    unauthorizedHandler?.();
    throw new Error("Not authenticated. Please sign in.");
  }
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`Could not load your roadmap (HTTP ${res.status})`);
  return (await res.json()) as SavedRoadmap;
}

export function toggleRoadmapWeek(
  roadmapId: string,
  weekNo: number,
  done: boolean,
): Promise<RoadmapProgress> {
  return callApi<RoadmapProgress>(
    `/users/me/roadmaps/${encodeURIComponent(roadmapId)}/progress`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ week_no: weekNo, done }),
    },
  );
}

export function fetchUserMastery(examId: string): Promise<UserMasteryResponse> {
  return callApi<UserMasteryResponse>(
    `/adaptive/mastery/${encodeURIComponent(examId)}`,
  );
}

/* ---------------- telegram ---------------- */

export function createTelegramLink(): Promise<TelegramLinkStartResponse> {
  return callApi<TelegramLinkStartResponse>("/notifications/telegram/link", {
    method: "POST",
  });
}

export function getTelegramStatus(): Promise<TelegramLinkStatusResponse> {
  return callApi<TelegramLinkStatusResponse>("/notifications/telegram/status");
}

export function unlinkTelegram(): Promise<{ status: string }> {
  return callApi<{ status: string }>("/notifications/telegram/link", {
    method: "DELETE",
  });
}
