import { describe, expect, it } from "vitest";
import { slugFor } from "./slug";

describe("slugFor", () => {
  it("preserves short ids instead of rejecting them", () => {
    expect(slugFor("AFCAT", "afcat")).toBe("afcat-afcat");
  });

  it("separates ids that used to share an 8-character prefix", () => {
    const a = slugFor("Same Title", "indian-army-agniveer-gd");
    const b = slugFor("Same Title", "indian-army-technical");
    expect(a).not.toBe(b);
  });

  it("normalises hyphens and underscores consistently", () => {
    expect(slugFor("Exam", "ABC-123_def")).toBe(slugFor("Exam", "abc123def"));
  });
});
