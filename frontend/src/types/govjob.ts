// Types mirroring the GovJob backend API (FastAPI, /api/v1)

export interface CandidateProfile {
  profile_id?: string;
  full_name?: string | null;
  email?: string | null;
  dob?: string | null;
  gender?: string | null;
  category?: string | null;
  is_pwd?: boolean | string | null;
  domicile_state?: string | null;
  highest_degree?: string | null;
  stream?: string | null;
  percentage_cgpa?: number | string | null;
  passing_year?: number | null;
  skills?: string[];
  raw_resume_text?: string | null;
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
  is_eligible?: boolean;
  is_last_attempt_age?: boolean;
  reasons_failed?: string[];
  syllabus_overlap_pct?: number | null;
  official_pdf_url?: string | null;
}

export interface IneligibleExam extends ExamMatchResult {
  reasons_failed: string[];
}

export interface EligibilityCheckResponse {
  candidate_name?: string | null;
  eligible_now: ExamMatchResult[];
  borderline_last_chance?: ExamMatchResult[];
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
  exam_name: string;
  total_duration_weeks: number;
  revision_strategy: string;
  weekly_breakdown: RoadmapWeek[];
}

export interface SyncLiveJobsResponse {
  status: string;
  new_jobs_discovered?: number;
  skipped_jobs?: number;
  total_active_jobs?: number;
  message?: string;
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

export interface CandidateProfileOut extends CandidateProfile {
  id: string;
}

export interface TelegramAlertResponse {
  status?: string;
  detail?: string;
  message?: string;
}

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

// ==========================================
// SATHI AI QUIZ, TELEMETRY & MASTERY TYPES
// ==========================================

export type MistakeCategory =
  | "Calculation / Rush Error"
  | "Conceptual Gap"
  | "Time-Sink Bottleneck"
  | "Unclassified Error";

export type TopicMasteryStatus = "Mastered" | "Moderate" | "Needs Revision";

export interface QuizQuestion {
  id: string;
  subject: string;
  topic: string;
  sub_topic: string;
  question: string;
  options: Record<string, string>; // e.g. { "A": "600", "B": "750", ... }
  // No correct_option/explanation: the server reveals them only after submit.
  difficulty: "Easy" | "Medium" | "Hard" | string;
  expected_time_sec: number;
  origin_type?: "REAL_PYQ" | "PYQ_STYLE" | string;
  pyq_year?: number | null;
  verification_badge?: string | null;
  source_title?: string | null;
  ca_month?: string | null;
  marks_correct?: number;
  negative_marks?: number;
  quality_score?: number;
}

// Alias for components importing QuestionItem
export type QuestionItem = QuizQuestion;

export interface QuizGenerateResponse {
  quiz_id: string;
  exam_id: string;
  topic: string;
  questions: QuizQuestion[];
  total_questions: number;
}

export interface QuestionSubmissionItem {
  question_id: string;
  selected_option: string;
  time_taken_sec: number;
}

export interface SubmitQuizPayload {
  exam_id: string;
  topic: string;
  answers: QuestionSubmissionItem[];
}

export interface DiagnosticItem {
  question_id: string;
  topic: string;
  sub_topic: string;
  mistake_type: MistakeCategory | string;
  is_repeated: boolean;
}

export interface QuestionReviewItem {
  question_id: string;
  question: string;
  options: Record<string, string>;
  selected_option: string;
  correct_option: string;
  explanation?: string | null;
  is_correct: boolean;
  time_taken_sec: number;
}

export interface QuizEvaluationResponse {
  quiz_id: string;
  total_attempted: number;
  correct_count: number;
  accuracy_pct: number;
  net_marks?: number;
  topic_status: TopicMasteryStatus;
  diagnostics: DiagnosticItem[];
  micro_revisions_added: string[];
  results: QuestionReviewItem[];
}

export interface ReportQuestionResponse {
  question_id: string;
  report_count: number;
  is_retired: boolean;
  quality_score?: number;
  reason_logged?: string;
}

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