/**
 * Mapping layer: ExamNotification (DB row as served by /eligibility/exams) →
 * the card model the feed renders. The backend does not store vacancies,
 * salary or applicant category, so the UI shows what is actually known:
 * age range, minimum percentage, deadline and the official PDF.
 */

import type { ExamNotification } from "../types";

export const STATES = [
  "All India",
  "Delhi",
  "Bihar",
  "Uttar Pradesh",
  "Maharashtra",
  "Rajasthan",
  "Madhya Pradesh",
  "Haryana",
  "Karnataka",
  "Tamil Nadu",
  "West Bengal",
  "Punjab",
  "Gujarat",
];

export interface FeedExam {
  id: string;
  title: string;
  department: string;
  postType: string;
  state: string;
  minPercentage: number | null;
  ageMin: number;
  ageMax: number;
  cutoffDate: string;
  examDate: string | null;
  lastDateISO: string;
  /** whole days until the application deadline; negative when closed */
  deadlineDays: number;
  isNew: boolean;
  topics: string[];
  degrees: string[];
  streams: string[];
  pdfUrl: string | null;
  /** Official online application portal — absent when not on file. */
  applyUrl: string | null;
  sourceUrl: string | null;
  lastChecked: string | null;
  allowsFinalYear: boolean | null;
}

const DAY_MS = 86_400_000;

/** Parse YYYY-MM-DD as a LOCAL date — `new Date(iso)` would be UTC midnight and shift a day in IST. */
function parseLocalDate(iso: string): Date | null {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso.trim());
  if (!m) return null;
  const d = new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
  return Number.isNaN(d.getTime()) ? null : d;
}

export function daysUntil(iso: string): number {
  const d = parseLocalDate(iso);
  if (!d) return 0;
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  return Math.ceil((d.getTime() - today.getTime()) / DAY_MS);
}

export function formatDateIN(iso: string | null): string {
  if (!iso) return "Not announced";
  const d = parseLocalDate(iso);
  if (!d) return iso;
  return d.toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function hoursSince(iso: string | null): number | null {
  if (!iso) return null;
  const d = parseLocalDate(iso);
  if (!d) return null;
  return (Date.now() - d.getTime()) / 3_600_000;
}

function coercePercentage(v: ExamNotification["min_percentage"]): number | null {
  if (v === null || v === undefined || v === "") return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

export function toFeedExam(e: ExamNotification): FeedExam {
  const postedHours = hoursSince(e.notification_date);
  return {
    id: e.id,
    title: e.title,
    department: e.organizing_body,
    postType: e.post_type,
    state: e.state_restriction?.trim() || "All India",
    minPercentage: coercePercentage(e.min_percentage),
    ageMin: e.min_age,
    ageMax: e.max_age_general,
    cutoffDate: e.age_cutoff_date,
    examDate: e.exam_date,
    lastDateISO: e.application_deadline,
    deadlineDays: daysUntil(e.application_deadline),
    isNew: postedHours !== null && postedHours >= 0 && postedHours < 72,
    topics: e.topics ?? [],
    degrees: e.allowed_degrees ?? [],
    streams: e.allowed_streams ?? [],
    pdfUrl: e.official_pdf_url,
    applyUrl: e.apply_url,
    sourceUrl: e.source_url,
    lastChecked: e.last_checked_at,
    allowsFinalYear: e.allows_final_year,
  };
}

/* ---------- admit cards ---------- */

export interface FeedAdmitCard {
  id: string;
  title: string;
  department: string;
  examName: string | null;
  /** whole days until the exam; null when the board has not published a date */
  examDays: number | null;
  examDateISO: string | null;
  notificationISO: string | null;
  admitUrl: string | null;
  sourceUrl: string | null;
  lastChecked: string | null;
  /** notification released within the last 72 h */
  isNew: boolean;
}

export function toFeedAdmitCard(a: import("../types").AdmitCard): FeedAdmitCard {
  const postedHours = hoursSince(a.notification_date);
  return {
    id: a.id,
    title: a.title,
    department: a.organizing_body,
    examName: a.exam_name,
    examDateISO: a.exam_date,
    examDays: a.exam_date ? daysUntil(a.exam_date) : null,
    notificationISO: a.notification_date,
    admitUrl: a.admit_url,
    sourceUrl: a.source_url,
    lastChecked: a.last_checked_at,
    isNew: postedHours !== null && postedHours >= 0 && postedHours < 72,
  };
}
