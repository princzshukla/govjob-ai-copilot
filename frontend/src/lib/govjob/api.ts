import type {
  CandidateProfile,
  EligibilityCheckResponse,
  MissingFieldPrompt,
  StudyRoadmapResponse,
  SyncLiveJobsResponse,
  TelegramAlertResponse,
  TelegramLinkStartResponse,
  TelegramLinkStatusResponse,
  QuizGenerateResponse,
  QuizEvaluationResponse,
  SubmitQuizPayload,
  UserMasteryResponse,
} from "@/types/govjob";

// Both names are read so the app keeps working with either the value written
// by setup.sh or a manually configured frontend/.env.
const API_BASE =
  import.meta.env["VITE_API_BASE_URL"] ??
  import.meta.env["VITE_GOVJOB_API_BASE"] ??
  "http://localhost:8000/api/v1";

const REQUEST_TIMEOUT_MS = 25000; // Increased to 25s to account for AI Groq question generation

const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;

export interface ParseResumeResult {
  extracted_profile: CandidateProfile;
  missing_fields: MissingFieldPrompt[];
  message: string;
}

async function fetchWithTimeout(input: string, init?: RequestInit): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    return await fetch(input, {
      ...init,
      // Session auth is an HttpOnly cookie, so cross-origin calls must include it.
      credentials: "include",
      signal: controller.signal,
    });
  } finally {
    clearTimeout(timer);
  }
}

async function callApi<T>(path: string, init?: RequestInit): Promise<T> {
  try {
    const res = await fetchWithTimeout(`${API_BASE}${path}`, init);
    if (!res.ok) {
      const err = (await res.json().catch(() => ({}))) as { detail?: string };
      throw new Error(err.detail || `Server returned HTTP ${res.status}: ${res.statusText}`);
    }
    return (await res.json()) as T;
  } catch (err) {
    console.error(`API Call failed on [${path}]:`, err);
    if (err instanceof Error) {
      if (err.name === "AbortError") {
        throw new Error("Request timed out. Please check if your FastAPI server is running.");
      }
      throw err;
    }
    throw new Error("Failed to communicate with GovJob backend.");
  }
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
 * Builds the strict `CandidateProfileCreate` payload.
 *
 * Missing statutory fields raise an error instead of being silently replaced
 * with placeholder data — otherwise a candidate could be judged against a
 * fictional date of birth, percentage or domicile.
 */
export function buildCandidatePayload(profile: CandidateProfile): Record<string, unknown> {
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

  const fullName = asTrimmedString(raw["full_name"]);
  const stream = asTrimmedString(raw["stream"]);
  const passingYear = raw["passing_year"];

  return {
    full_name: fullName || null,
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

// ==========================================
// RESUME & ELIGIBILITY ENDPOINTS
// ==========================================

export function parseResume(file: File): Promise<ParseResumeResult> {
  const formData = new FormData();
  formData.append("file", file);
  return callApi<ParseResumeResult>("/candidate/parse-resume", {
    method: "POST",
    body: formData,
  });
}

export function checkEligibility(
  profile: CandidateProfile,
  primaryExamId: string,
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

export function generateRoadmap(
  examId: string,
  targetWeeks: number,
): Promise<StudyRoadmapResponse> {
  return callApi<StudyRoadmapResponse>(
    `/eligibility/generate-roadmap/${encodeURIComponent(examId)}?target_weeks=${targetWeeks}`,
    { method: "POST" },
  );
}

export function syncLiveJobs(): Promise<SyncLiveJobsResponse> {
  return callApi<SyncLiveJobsResponse>("/eligibility/sync-live-jobs", {
    method: "POST",
  });
}

export function sendTelegramAlert(payload: {
  exam_title: string;
  application_deadline: string;
  days_left: number;
}): Promise<TelegramAlertResponse> {
  // No chat_id: the backend sends only to the session user's verified chat.
  return callApi<TelegramAlertResponse>("/notifications/send-deadline-alert", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

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

// ==========================================
// ADAPTIVE DRILL & MASTERY ENDPOINTS
// ==========================================

export async function fetchAdaptiveQuiz(
  examId: string,
  subject: string,
  topic: string,
  count: number = 3,
): Promise<QuizGenerateResponse> {
  return callApi<QuizGenerateResponse>(
    `/adaptive/quiz?exam_id=${encodeURIComponent(examId)}&subject=${encodeURIComponent(
      subject,
    )}&topic=${encodeURIComponent(topic)}&count=${count}`,
  );
}

export async function submitAdaptiveQuiz(
  payload: SubmitQuizPayload,
): Promise<QuizEvaluationResponse> {
  return callApi<QuizEvaluationResponse>("/adaptive/submit-quiz", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function fetchUserMastery(
  examId: string,
): Promise<UserMasteryResponse> {
  return callApi<UserMasteryResponse>(
    `/adaptive/mastery/${encodeURIComponent(examId)}`,
  );
}
