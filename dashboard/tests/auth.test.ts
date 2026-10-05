import { describe, expect, it } from "vitest";
import { passwordMatches } from "@/lib/auth";

describe("passwordMatches", () => {
  it("accepts the exact password", () => {
    expect(passwordMatches("s3cret", "s3cret")).toBe(true);
  });

  it("rejects a wrong password, including one that is only a prefix", () => {
    expect(passwordMatches("s3cre", "s3cret")).toBe(false);
    expect(passwordMatches("s3cretx", "s3cret")).toBe(false);
  });

  it("fails closed when the server has no password configured", () => {
    expect(passwordMatches("anything", undefined)).toBe(false);
    expect(passwordMatches(undefined, undefined)).toBe(false);
  });

  it("rejects a missing candidate", () => {
    expect(passwordMatches(undefined, "s3cret")).toBe(false);
    expect(passwordMatches("", "s3cret")).toBe(false);
  });
});
