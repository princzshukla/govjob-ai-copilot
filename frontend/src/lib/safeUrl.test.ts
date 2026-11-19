import { describe, expect, it } from "vitest";
import { safeUrl } from "./safeUrl";

describe("safeUrl", () => {
  it("keeps http(s) URLs", () => {
    expect(safeUrl("https://ssc.gov.in/notice.pdf")).toBe("https://ssc.gov.in/notice.pdf");
    expect(safeUrl("http://example.com/apply")).toBe("http://example.com/apply");
  });

  it("rejects executable and non-http schemes", () => {
    expect(safeUrl("javascript:alert(1)")).toBeUndefined();
    expect(safeUrl("JaVaScRiPt:alert(1)")).toBeUndefined();
    expect(safeUrl("data:text/html,<script>alert(1)</script>")).toBeUndefined();
    expect(safeUrl("file:///etc/passwd")).toBeUndefined();
    expect(safeUrl("tel:123")).toBeUndefined();
  });

  it("rejects empty and malformed values", () => {
    expect(safeUrl(null)).toBeUndefined();
    expect(safeUrl(undefined)).toBeUndefined();
    expect(safeUrl("   ")).toBeUndefined();
    expect(safeUrl("http://[::1")).toBeUndefined();
  });
});
