/** Wire types for the backend REST API. Mirrors `endpoint.md`. */

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
