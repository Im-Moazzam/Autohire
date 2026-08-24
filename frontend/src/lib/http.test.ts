import { describe, expect, it } from "vitest";
import { ApiError, apiErrorCode, apiErrorMessage } from "./http";

describe("apiErrorMessage (TS-07)", () => {
  it("points REAUTH_REQUIRED at the reconnect banner, not the raw backend message", () => {
    const err = new ApiError("failed", 409, {
      code: "REAUTH_REQUIRED",
      message: "Google authorization has expired.",
    });
    expect(apiErrorMessage(err)).toMatch(/reconnect/i);
    expect(apiErrorCode(err)).toBe("REAUTH_REQUIRED");
  });

  it("still surfaces the backend message for any other error code", () => {
    const err = new ApiError("failed", 409, {
      code: "JOB_CLOSED",
      message: "This posting is no longer accepting applications.",
    });
    expect(apiErrorMessage(err)).toBe(
      "This posting is no longer accepting applications.",
    );
  });

  it("falls back for a non-ApiError", () => {
    expect(apiErrorMessage(new Error("network down"), "fallback text")).toBe(
      "fallback text",
    );
  });
});
