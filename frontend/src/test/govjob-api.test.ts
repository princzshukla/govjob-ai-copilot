import { describe, expect, it } from "vitest";
import { buildCandidatePayload, toIsoDate } from "@/lib/govjob/api";

const COMPLETE_PROFILE = {
  full_name: "  Test User  ",
  dob: "2004-06-10",
  category: "OBC",
  domicile_state: "Delhi",
  highest_degree: "B.Tech",
  stream: "Computer Science",
  percentage_cgpa: 72.5,
  passing_year: 2025,
};

describe("toIsoDate", () => {
  it("passes through ISO dates", () => {
    expect(toIsoDate("2004-06-10")).toBe("2004-06-10");
  });

  it("returns null for unusable values", () => {
    expect(toIsoDate("not-a-date")).toBeNull();
    expect(toIsoDate(null)).toBeNull();
    expect(toIsoDate("")).toBeNull();
  });
});

describe("buildCandidatePayload", () => {
  it("normalises a complete profile", () => {
    const payload = buildCandidatePayload(COMPLETE_PROFILE);

    expect(payload["full_name"]).toBe("Test User");
    expect(payload["category"]).toBe("OBC-NCL");
    expect(payload["percentage_cgpa"]).toBe(72.5);
    expect(payload["is_pwd"]).toBe(false);
    expect(payload["stream"]).toBe("Computer Science");
  });

  it("never invents statutory fields the candidate did not provide", () => {
    expect(() => buildCandidatePayload({ full_name: "Test" })).toThrow(/Date of birth/);
    expect(() => buildCandidatePayload({ full_name: "Test" })).toThrow(/Domicile state/);
    expect(() => buildCandidatePayload({ full_name: "Test" })).toThrow(
      /Graduation percentage/,
    );
  });

  it("coerces a string percentage and defaults an unspecified stream to Any", () => {
    const payload = buildCandidatePayload({
      ...COMPLETE_PROFILE,
      percentage_cgpa: "64.25",
      stream: "",
    });

    expect(payload["percentage_cgpa"]).toBe(64.25);
    expect(payload["stream"]).toBe("Any");
  });

  it("maps the PwBD select value correctly", () => {
    expect(buildCandidatePayload({ ...COMPLETE_PROFILE, is_pwd: "No" })["is_pwd"]).toBe(false);
    expect(buildCandidatePayload({ ...COMPLETE_PROFILE, is_pwd: "Yes" })["is_pwd"]).toBe(true);
  });
});
