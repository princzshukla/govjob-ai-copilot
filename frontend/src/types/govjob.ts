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

// ==========================================
// ADAPTIVE QUIZ & MASTERY TYPES
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
  correct_option: string;
  explanation: string;
  difficulty: "Easy" | "Medium" | "Hard" | string;
  expected_time_sec: number;
}

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
  user_id: string;
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

export interface QuizEvaluationResponse {
  quiz_id: string;
  total_attempted: number;
  correct_count: number;
  accuracy_pct: number;
  topic_status: TopicMasteryStatus;
  diagnostics: DiagnosticItem[];
  micro_revisions_added: string[];
  roadmap_structure_changed: boolean;
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
  user_id: string;
  exam_id: string;
  topics: TopicMasteryItem[];
}