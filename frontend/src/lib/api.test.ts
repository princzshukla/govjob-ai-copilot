import { describe, expect, it } from "vitest";
import {
  buildCandidatePayload,
  buildProfilePayload,
  detailToMessage,
  toIsoDate,
} from "./api";

describe("detailToMessage", () => {
  it("passes a string detail through", () => {
    expect(detailToMessage("Not authenticated", "fallback")).toBe("Not authenticated");
  });

  it("flattens FastAPI 422 validation arrays into readable text", () => {
    const detail = [
      { loc: ["body", "dob"], msg: "field required" },
      { loc: ["body", "percentage_cgpa"], msg: "value is not a valid number" },
    ];
    expect(detailToMessage(detail, "fallback")).toBe(
      "dob: field required. percentage_cgpa: value is not a valid number",
    );
  });

  it("defaults a message-less entry to 'Invalid value'", () => {
    expect(detailToMessage([{ loc: ["body"] }], "fallback")).toBe("Invalid value");
  });

  it("falls back only when the array yields nothing usable", () => {
    expect(detailToMessage([], "fallback")).toBe("fallback");
    expect(detailToMessage([null, 42], "fallback")).toBe("fallback");
  });

  it("falls back for undefined / objects", () => {
    expect(detailToMessage(undefined, "fallback")).toBe("fallback");
    expect(detailToMessage({ detail: true }, "fallback")).toBe("fallback");
  });
});

describe("toIsoDate", () => {
  it("passes ISO dates through untouched", () => {
    expect(toIsoDate("2004-06-10")).toBe("2004-06-10");
  });

  it("parses other date formats", () => {
    expect(toIsoDate("10 Jun 2004")).toBe("2004-06-10");
  });

  it("returns null for garbage", () => {
    expect(toIsoDate("not a date")).toBeNull();
    expect(toIsoDate("")).toBeNull();
    expect(toIsoDate(42)).toBeNull();
  });
});

const fullProfile = {
  full_name: "Aarav Kumar",
  dob: "2002-01-01",
  gender: "Male",
  category: "OBC",
  domicile_state: "Bihar",
  highest_degree: "Graduate",
  stream: "Computer Science",
  percentage_cgpa: 58,
  passing_year: "2024",
};

describe("buildCandidatePayload", () => {
  it("normalises OBC to OBC-NCL and keeps the strict shape", () => {
    const p = buildCandidatePayload(fullProfile);
    expect(p["category"]).toBe("OBC-NCL");
    expect(p["dob"]).toBe("2002-01-01");
    expect(p["percentage_cgpa"]).toBe(58);
    expect(p["passing_year"]).toBe(2024);
  });

  it("accepts string percentages", () => {
    const p = buildCandidatePayload({ ...fullProfile, percentage_cgpa: "58.5" });
    expect(p["percentage_cgpa"]).toBe(58.5);
  });

  it("throws listing every missing statutory field", () => {
    expect(() => buildCandidatePayload({})).toThrow(/Date of birth/);
    expect(() => buildCandidatePayload({})).toThrow(/Reservation category/);
    expect(() => buildCandidatePayload({})).toThrow(/Domicile state/);
    expect(() => buildCandidatePayload({})).toThrow(/Highest qualification/);
    expect(() => buildCandidatePayload({})).toThrow(/Graduation percentage/);
  });
});

describe("buildProfilePayload", () => {
  it("omits missing fields and defaults category to General", () => {
    const p = buildProfilePayload({ full_name: "Aarav" });
    expect(p).toEqual({ full_name: "Aarav", category: "General" });
  });

  it("coerces types where the backend is strict", () => {
    const p = buildProfilePayload({
      percentage_cgpa: "72.25",
      passing_year: "2024",
      is_pwd: "yes",
    });
    expect(p["percentage_cgpa"]).toBe(72.25);
    expect(p["passing_year"]).toBe(2024);
    expect(p["is_pwd"]).toBe(true);
  });
});
