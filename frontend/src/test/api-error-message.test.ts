import { describe, expect, it } from "vitest";

import { detailToMessage } from "@/lib/govjob/api";

describe("detailToMessage", () => {
  it("passes string details through unchanged", () => {
    expect(detailToMessage("Invalid email or password", "fallback")).toBe(
      "Invalid email or password",
    );
  });

  it("renders the FastAPI 422 list as a readable message", () => {
    expect(
      detailToMessage(
        [
          {
            type: "value_error",
            loc: ["body", "phone"],
            msg: "Phone must be in E.164 format, for example +919876543210",
            ctx: {},
          },
        ],
        "fallback",
      ),
    ).toBe("phone: Phone must be in E.164 format, for example +919876543210");
  });

  it("joins multiple validation errors", () => {
    expect(
      detailToMessage(
        [
          { loc: ["body", "email"], msg: "field required" },
          { loc: ["body", "password"], msg: "string should have at least 8 characters" },
        ],
        "fallback",
      ),
    ).toBe("email: field required. password: string should have at least 8 characters");
  });

  it("falls back when detail is missing or of an unknown shape", () => {
    expect(detailToMessage(undefined, "fallback")).toBe("fallback");
    expect(detailToMessage(42 as unknown, "fallback")).toBe("fallback");
    expect(detailToMessage([], "fallback")).toBe("fallback");
  });
});
