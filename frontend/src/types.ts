/** Wire types for the backend REST API. Mirrors `endpoint.md` / backend schemas. */

export interface ExamNotification {
  id: string;
  title: string;
  organizing_body: string;
  post_type: string;
  notification_date: string | null;
  application_deadline: string; // ISO date, YYYY-MM-DD
  exam_date: string | null;
  official_pdf_url: string | null;
  min_age: number;
  max_age_general: number;
  age_cutoff_date: string;
  allowed_degrees: string[];
  allowed_streams: string[] | null;
  /** FastAPI serialises Numeric as a string, e.g. "60.00" — always coerce with Number(). */
  min_percentage: number | string | null;
  topics: string[] | null;
  /** null = Pan-India central vacancy */
  state_restriction: string | null;
  allows_final_year: boolean | null;
  max_attempts: number | null;
  /** Provenance — every exam links the official source. */
  source_url: string | null;
  last_checked_at: string | null;
  is_active: boolean;
}

export interface ExamsListResponse {
  total: number;
  exams: ExamNotification[];
}

/* ---------- candidate profile ---------- */

export interface CandidateProfile {
  profile_id?: string;
  full_name?: string | null;
  dob?: string | null;
  gender?: string | null;
  category?: string | null;
  is_pwd?: boolean | string | null;
  domicile_state?: string | null;
  highest_degree?: string | null;
  stream?: string | null;
  percentage_cgpa?: number | string | null;
  passing_year?: number | string | null;
  skills?: string[];
  [key: string]: unknown;
}

export interface SaveProfileResponse {
  profile_id: string;
  status: "created" | "updated";
  profile: CandidateProfile;
}

export interface MissingFieldPrompt {
  field_name: string;
  label: string;
  question: string;
  input_type: "text" | "number" | "date" | "select" | string;
  options?: string[];
}

export interface ParseResumeResult {
  extracted_profile: CandidateProfile;
  missing_fields: MissingFieldPrompt[];
  message: string;
}

export interface ClaimDraftResponse {
  status: "claimed" | "already_claimed";
  profile: CandidateProfile;
}

/* ---------- eligibility ---------- */

export interface RuleExplanation {
  rule: string;
  candidate_value: string;
  required_value: string;
  status: "passed" | "failed" | "needs_check";
  message: string;
}

export interface ExamMatchResult {
  exam_id: string;
  title: string;
  organizing_body: string;
  post_type: string;
  application_deadline: string;
  exam_date: string | null;
  official_pdf_url: string | null;
  is_eligible: boolean;
  candidate_age_at_cutoff: number;
  max_allowed_age: number;
  is_last_attempt_age: boolean;
  reasons_failed: string[];
  syllabus_overlap_pct: number | null;
  verdict: "eligible" | "check_manually" | "ineligible";
  check_manually: boolean;
  rules: RuleExplanation[];
  source_url?: string | null;
  last_checked_at?: string | null;
}

export interface EligibilityCheckResponse {
  candidate_name: string | null;
  eligible_now: ExamMatchResult[];
  borderline_last_chance: ExamMatchResult[];
  ineligible: ExamMatchResult[];
  check_manually: ExamMatchResult[];
}

/* ---------- roadmap ---------- */

export interface RoadmapWeek {
  week_number: number;
  focus_subject: string;
  phase: string;
  topics: string[];
  practice_goal: string;
  recommended_resources: string[];
}

export interface StudyRoadmapResponse {
  exam_name: string;
  total_duration_weeks: number;
  revision_strategy: string;
  weekly_breakdown: RoadmapWeek[];
}

export interface SavedRoadmap {
  roadmap_id: string;
  exam_id: string;
  target_weeks: number;
  roadmap: StudyRoadmapResponse;
  created_at: string;
  completed_weeks: number[];
  completed_count: number;
  percent: number;
}

export interface RoadmapProgress {
  roadmap_id: string;
  target_weeks: number;
  completed_weeks: number[];
  completed_count: number;
  percent: number;
}

/* ---------- auth / account ---------- */

export interface UserOut {
  id: number;
  email: string;
  full_name: string | null;
  phone: string | null;
  created_at: string;
}

export interface RegisterPayload {
  email: string;
  password: string;
  full_name: string;
  phone?: string | null;
}

/* ---------- telegram ---------- */

export interface TelegramLinkStartResponse {
  code: string;
  expires_at: string;
  bot_username: string;
}

export interface TelegramLinkStatusResponse {
  linked: boolean;
  chat_id?: string | null;
  verified_at?: string | null;
}

/* ---------- adaptive (mastery badges) ---------- */

export type TopicMasteryStatus = "Mastered" | "Moderate" | "Needs Revision";

export interface TopicMasteryItem {
  topic: string;
  subject: string;
  accuracy_ema: number;
  attempts_count: number;
  status: TopicMasteryStatus;
  last_reviewed_at: string;
}

export interface UserMasteryResponse {
  user_id: number;
  exam_id: string;
  topics: TopicMasteryItem[];
}
