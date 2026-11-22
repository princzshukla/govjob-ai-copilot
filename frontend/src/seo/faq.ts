import type { ExamNotification } from "../types";
import { formatDateIN } from "../lib/exams";

export interface QA {
  question: string;
  answer: string;
}

const date = (value?: string | null) =>
  value ? formatDateIN(value) : "not stated in the notification";

/** Shared with prerender.mjs so FAQPage schema always matches visible text. */
export function jobFaqs(exam: ExamNotification): QA[] {
  const degrees = exam.allowed_degrees?.length ? exam.allowed_degrees.join(", ") : "the required qualification";
  const minPercent = exam.min_percentage ? ` and at least ${Number(exam.min_percentage)}%` : "";
  const age = `${exam.min_age}–${exam.max_age_general} years as of ${date(exam.age_cutoff_date)}`;
  const lastDate = date(exam.application_deadline);
  const examDate = date(exam.exam_date);

  return [
    {
      question: `Who can apply for ${exam.title}?`,
      answer: `You need ${degrees}${minPercent}. Age must be ${age}${exam.state_restriction ? `, and the vacancy is restricted to ${exam.state_restriction}` : " and the vacancy is open across India"}.`,
    },
    {
      question: `What is the age limit for ${exam.title}?`,
      answer: `The age band is ${age}. Candidates outside this band cannot apply unless the board has published a relaxation in the official notification.`,
    },
    {
      question: `What is the last date to apply for ${exam.title}?`,
      answer: `The application deadline on file is ${lastDate}. We check this against the official notice; confirm it on the application portal before you submit.`,
    },
    {
      question: `When is the ${exam.title} exam?`,
      answer: `The exam date on file is ${examDate}. If the board has not announced it yet, we leave it blank rather than guess.`,
    },
    {
      question: `Where is the official notification for ${exam.title}?`,
      answer: exam.official_pdf_url
        ? "The official PDF is linked in the Sources section below, along with the page we checked it against."
        : "We only publish a page when an official source is on file; use the organising body's website until this notification is verified.",
    },
  ];
}
