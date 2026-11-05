// Types mirroring the GovJob backend API (FastAPI, /api/v1)

export interface CandidateProfile {
  full_name?: string | null;
  email?: string | null;
  dob?: string | null;
  gender?: string | null;
  category?: string | null;
  domicile_state?: string | null;
  highest_degree?: string | null;
  stream?: string | null;
  percentage_cgpa?: number | null;
  [key: string]: unknown;
}

export interface MissingFieldPrompt {
  field_name: string;
  label: string;
  question: string;
  input_type: "text" | "number" | "date" | "select";
  options?: string[];
}

export interface ExamMatchResult {
  exam_id: string;
  title: string;
  organizing_body: string;
  post_type: string;
  application_deadline: string;
  exam_date?: string | null;
  candidate_age_at_cutoff: number;
  max_allowed_age: number;
  syllabus_overlap_pct?: number | null;
  official_pdf_url?: string | null;
}

export interface IneligibleExam extends ExamMatchResult {
  reasons_failed: string[];
}

export interface EligibilityCheckResponse {
  eligible_now: ExamMatchResult[];
  ineligible: IneligibleExam[];
}

export interface RoadmapWeek {
  week_number: number;
  focus_subject: string;
  phase: string;
  topics: string[];
  practice_goal: string;
  recommended_resources: string[];
}

export interface StudyRoadmapResponse {
  exam_id: string;
  exam_name: string;
  total_duration_weeks: number;
  revision_strategy: string;
  weekly_breakdown: RoadmapWeek[];
}

export interface SyncLiveJobsResponse {
  status: string;
  new_jobs_discovered?: number;
  total_active_jobs?: number;
  message?: string;
}

export interface TelegramAlertResponse {
  status?: string;
  detail?: string;
  message?: string;
}
