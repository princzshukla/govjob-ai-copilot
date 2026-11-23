import { describe, expect, it } from "vitest";
import { buildCandidatePayload } from "./api";
import { withProfileDefaults } from "./profile";

describe("withProfileDefaults", () => {
  it("puts General and Male into state for an empty profile", () => {
    expect(withProfileDefaults({})).toEqual({ category: "General", gender: "Male" });
  });

  it("keeps values the user or parser supplied", () => {
    expect(withProfileDefaults({ category: "OBC-NCL", gender: "Female" })).toMatchObject({
      category: "OBC-NCL",
      gender: "Female",
    });
  });

  it("treats null and whitespace-only values as missing", () => {
    expect(withProfileDefaults({ category: null, gender: "  " })).toMatchObject({
      category: "General",
      gender: "Male",
    });
  });

  it("lets eligibility run after a resume parse with no category, without reselecting", () => {
    const profile = withProfileDefaults({
      full_name: "Aarav",
      dob: "2000-01-01",
      domicile_state: "Delhi",
      highest_degree: "B.Tech",
      percentage_cgpa: 60,
    });
    const payload = buildCandidatePayload(profile);
    expect(payload.category).toBe("General");
  });
});
