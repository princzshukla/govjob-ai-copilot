import { beforeEach, describe, expect, it, vi } from "vitest";
import { checkEligibility, parseResume, withDemoDefaults } from "@/lib/govjob/api";
import { DEMO_ELIGIBILITY, buildDemoRoadmap } from "@/lib/govjob/demo-data";

beforeEach(() => {
  vi.unstubAllGlobals();
  vi.stubGlobal(
    "fetch",
    vi.fn().mockRejectedValue(new TypeError("fetch failed: backend unreachable")),
  );
});

describe("govjob demo fallback", () => {
  it("serves demo eligibility data when the backend is unreachable", async () => {
    const { data, demo } = await checkEligibility({ full_name: "Test User" }, "ssc-cgl-general");
    expect(demo).toBe(true);
    expect(data.eligible_now.length).toBeGreaterThan(0);
    expect(data.eligible_now[0]!.exam_id).toBe(DEMO_ELIGIBILITY.eligible_now[0]!.exam_id);
    expect(data.ineligible[0]!.reasons_failed.length).toBeGreaterThan(0);
  });

  it("serves a demo parsed profile when resume parsing fails", async () => {
    const file = new File(["%PDF-1.4 fake"], "resume.pdf", { type: "application/pdf" });
    const { data, demo } = await parseResume(file);
    expect(demo).toBe(true);
    expect(data.extracted_profile.full_name).toBe("Aarav Sharma");
    expect(data.missing_fields.length).toBeGreaterThan(0);
  });

  it("builds a demo roadmap of exactly the requested length", () => {
    for (const weeks of [8, 12, 24]) {
      const roadmap = buildDemoRoadmap("ssc-cgl-general", "SSC CGL 2026", weeks);
      expect(roadmap.weekly_breakdown).toHaveLength(weeks);
      expect(roadmap.weekly_breakdown[weeks - 1]!.week_number).toBe(weeks);
      expect(roadmap.weekly_breakdown[0]!.topics.length).toBeGreaterThan(0);
    }
  });

  it("fills statutory defaults for missing profile fields", () => {
    const payload = withDemoDefaults({ full_name: "Test" });
    expect(payload.gender).toBe("Male");
    expect(payload.category).toBe("General");
    expect(payload.domicile_state).toBe("Delhi");
    expect(payload.percentage_cgpa).toBe(60.0);
  });
});
