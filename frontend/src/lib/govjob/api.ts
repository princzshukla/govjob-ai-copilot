import type {
  CandidateProfile,
  EligibilityCheckResponse,
  MissingFieldPrompt,
  StudyRoadmapResponse,
  SyncLiveJobsResponse,
  TelegramAlertResponse,
} from "@/types/govjob";
import {
  DEMO_ELIGIBILITY,
  DEMO_MISSING_FIELDS,
  DEMO_PROFILE,
  buildDemoRoadmap,
  demoSyncLiveJobs,
} from "./demo-data";

/**
 * GovJob API client with a graceful demo fallback:
 * every call first tries the real FastAPI backend, and if it is unreachable
 * or fails, returns realistic demo data instead so the UI never dead-ends.
 */

const API_BASE = import.meta.env["VITE_API_BASE_URL"] ?? "http://localhost:8000/api/v1";
const REQUEST_TIMEOUT_MS = 4000;

export interface ApiResult<T> {
  data: T;
  /** true when the real backend was unreachable and demo data was served */
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
  init: RequestInit | undefined,
  demo: T,
): Promise<ApiResult<T>> {
  try {
    const res = await fetchWithTimeout(`${API_BASE}${path}`, init);
    if (!res.ok) {
      const err = await res.json().catch(() => ({}) as { detail?: string });
      throw new Error(err.detail || `Request failed (${res.status})`);
    }
    return { data: (await res.json()) as T, demo: false };
  } catch (err) {
    console.error("API Call failed:", path, err);
    // Backend responded with HTTP error
    if (err instanceof Error && err.message.startsWith("Request failed")) {
      throw err;
    }
    // Return demo fallback but log a clear warning
    console.warn(`Falling back to demo data for endpoint: ${path}`);
    return { data: demo, demo: true };
  }
}

export function withDemoDefaults(profile: CandidateProfile): CandidateProfile {
  return {
    ...profile,
    gender: profile.gender || "Male",
    category: profile.category || "General",
    domicile_state: profile.domicile_state || "Delhi",
    highest_degree: profile.highest_degree || "Any Graduate",
    stream: profile.stream || "Any",
    percentage_cgpa: profile.percentage_cgpa ?? 60.0,
  };
}

export function parseResume(file: File): Promise<ApiResult<ParseResumeResult>> {
  const formData = new FormData();
  formData.append("file", file);
  return callApi<ParseResumeResult>(
    "/candidate/parse-resume",
    { method: "POST", body: formData },
    {
      extracted_profile: DEMO_PROFILE,
      missing_fields: DEMO_MISSING_FIELDS,
      message: "Demo mode: sample resume parsed. Connect the backend to analyse your real resume.",
    },
  );
}

export function checkEligibility(
  profile: CandidateProfile,
  primaryExamId: string,
): Promise<ApiResult<EligibilityCheckResponse>> {
  return callApi<EligibilityCheckResponse>(
    `/eligibility/check?primary_exam_id=${encodeURIComponent(primaryExamId)}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(withDemoDefaults(profile)),
    },
    DEMO_ELIGIBILITY,
  );
}

export function generateRoadmap(
  examId: string,
  targetWeeks: number,
  examName: string,
): Promise<ApiResult<StudyRoadmapResponse>> {
  return callApi<StudyRoadmapResponse>(
    `/eligibility/generate-roadmap/${encodeURIComponent(examId)}?target_weeks=${targetWeeks}`,
    { method: "POST" },
    buildDemoRoadmap(examId, examName, targetWeeks),
  );
}

export function syncLiveJobs(): Promise<ApiResult<SyncLiveJobsResponse>> {
  return callApi<SyncLiveJobsResponse>(
    "/eligibility/sync-live-jobs",
    { method: "POST" },
    demoSyncLiveJobs(),
  );
}

export function sendTelegramAlert(payload: {
  chat_id: string;
  exam_title: string;
  application_deadline: string;
  days_left: number;
}): Promise<ApiResult<TelegramAlertResponse>> {
  return callApi<TelegramAlertResponse>(
    "/notifications/send-deadline-alert",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    },
    {
      status: "success",
      message: "Demo alert dispatched (backend offline). No real Telegram message was sent.",
    },
  );
}
