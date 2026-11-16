import { describe, expect, it } from "vitest";
import { daysUntil, toFeedExam } from "./exams";
import type { ExamNotification } from "../types";

function futureISO(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() + days);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

const base: ExamNotification = {
  id: "exam-1",
  title: "Test Notification",
  organizing_body: "Staff Selection Commission",
  post_type: "Central Govt",
  notification_date: "2026-11-10",
  application_deadline: futureISO(30),
  exam_date: null,
  official_pdf_url: "https://example.gov.in/notice.pdf",
  min_age: 18,
  max_age_general: 27,
  age_cutoff_date: "2026-08-01",
  allowed_degrees: ["Any Graduate"],
  allowed_streams: null,
  min_percentage: "60.00",
  topics: ["Reasoning", "Quant"],
  state_restriction: null,
  allows_final_year: null,
  max_attempts: null,
  source_url: "https://example.gov.in",
  last_checked_at: "2026-11-16",
  is_active: true,
};

describe("toFeedExam", () => {
  it("maps a null state restriction to All India", () => {
    expect(toFeedExam(base).state).toBe("All India");
  });

  it("coerces string percentages from the API", () => {
    expect(toFeedExam(base).minPercentage).toBe(60);
  });

  it("keeps allowed streams and topics for the details panel", () => {
    const withStreams = { ...base, allowed_streams: ["Computer Science", "IT"] };
    expect(toFeedExam(withStreams).streams).toEqual(["Computer Science", "IT"]);
    expect(toFeedExam(base).topics).toEqual(["Reasoning", "Quant"]);
  });

});

describe("daysUntil", () => {
  it("counts whole days ahead of today", () => {
    const target = new Date();
    target.setDate(target.getDate() + 10);
    const iso = `${target.getFullYear()}-${String(target.getMonth() + 1).padStart(2, "0")}-${String(
      target.getDate(),
    ).padStart(2, "0")}`;
    expect(daysUntil(iso)).toBe(10);
  });
});
