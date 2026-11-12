import type {
  CandidateProfile,
  EligibilityCheckResponse,
  MissingFieldPrompt,
  StudyRoadmapResponse,
  SyncLiveJobsResponse,
  TelegramAlertResponse,
  QuizGenerateResponse,
  QuizEvaluationResponse,
  SubmitQuizPayload,
  UserMasteryResponse,
} from "@/types/govjob";

const API_BASE = import.meta.env["VITE_API_BASE_URL"] ?? "http://localhost:8000/api/v1";
const REQUEST_TIMEOUT_MS = 25000; // Increased to 25s to account for AI Groq question generation

export interface ApiResult<T> {
  data: T;
  demo: boolean;
}

export interface ParseResumeResult {
  extracted_profile: CandidateProfile;
  missing_fields: MissingFieldPrompt[];
  message: string;
}

async function fetchWithTimeout(input: string, init?: RequestInit): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    return await fetch(input, { ...init, signal: controller.signal });
  } finally {
    clearTimeout(timer);
  }
}

async function callApi<T>(
  path: string,
  init?: RequestInit,
): Promise<ApiResult<T>> {
  try {
    const res = await fetchWithTimeout(`${API_BASE}${path}`, init);
    if (!res.ok) {
      const err = await res.json().catch(() => ({}) as { detail?: string });
      throw new Error(err.detail || `Server returned HTTP ${res.status}: ${res.statusText}`);
    }
    const data = (await res.json()) as T;
    return { data, demo: false };
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

// ==========================================
// RESUME & ELIGIBILITY ENDPOINTS
// ==========================================

export function parseResume(file: File): Promise<ApiResult<ParseResumeResult>> {
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
): Promise<ApiResult<EligibilityCheckResponse>> {
  const raw = profile as Record<string, any>;

  // Ensure valid date string YYYY-MM-DD
  const rawDate = raw["dob"] || raw["date_of_birth"];
  const validDob = rawDate && /^\d{4}-\d{2}-\d{2}$/.test(rawDate) ? rawDate : "2004-06-10";

  // Ensure category aligns with CandidateProfileCreate: General, OBC-NCL, SC, ST, EWS
  let category = raw["category"] || "General";
  if (category === "OBC") category = "OBC-NCL";

  // Build the strict CandidateProfileCreate payload
  const sanitizedPayload = {
    full_name: raw["full_name"]?.trim() || "Candidate",
    dob: validDob,
    gender: raw["gender"] || "Male",
    category: category,
    is_pwd: Boolean(raw["is_pwd"] ?? raw["physical_disability"] ?? false),
    domicile_state: raw["domicile_state"]?.trim() || "Delhi",
    highest_degree: raw["highest_degree"]?.trim() || "12th",
    stream: raw["stream"]?.trim() || "Any",
    percentage_cgpa: Number(raw["percentage_cgpa"]) || 60.0,
    passing_year: raw["passing_year"] ? Number(raw["passing_year"]) : 2022,
    skills: Array.isArray(raw["skills"]) ? raw["skills"] : [],
  };

  return callApi<EligibilityCheckResponse>(
    `/eligibility/check?primary_exam_id=${encodeURIComponent(primaryExamId)}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(sanitizedPayload),
    },
  );
}

export function generateRoadmap(
  examId: string,
  targetWeeks: number,
  examName: string,
): Promise<ApiResult<StudyRoadmapResponse>> {
  return callApi<StudyRoadmapResponse>(
    `/eligibility/generate-roadmap/${encodeURIComponent(examId)}?target_weeks=${targetWeeks}&exam_name=${encodeURIComponent(examName)}`,
    { method: "POST" },
  );
}

export function syncLiveJobs(): Promise<ApiResult<SyncLiveJobsResponse>> {
  return callApi<SyncLiveJobsResponse>("/eligibility/sync-live-jobs", {
    method: "POST",
  });
}

export function sendTelegramAlert(payload: {
  chat_id: string;
  exam_title: string;
  application_deadline: string;
  days_left: number;
}): Promise<ApiResult<TelegramAlertResponse>> {
  return callApi<TelegramAlertResponse>("/notifications/send-deadline-alert", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
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
  const result = await callApi<QuizGenerateResponse>(
    `/adaptive/quiz?exam_id=${encodeURIComponent(examId)}&subject=${encodeURIComponent(
      subject,
    )}&topic=${encodeURIComponent(topic)}&count=${count}`,
  );
  return result.data;
}

export async function submitAdaptiveQuiz(
  payload: SubmitQuizPayload,
): Promise<QuizEvaluationResponse> {
  const result = await callApi<QuizEvaluationResponse>("/adaptive/submit-quiz", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return result.data;
}

export async function fetchUserMastery(
  userId: string,
  examId: string,
): Promise<UserMasteryResponse> {
  const result = await callApi<UserMasteryResponse>(
    `/adaptive/mastery/${encodeURIComponent(userId)}/${encodeURIComponent(examId)}`,
  );
  return result.data;
}