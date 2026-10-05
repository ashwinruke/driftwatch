import { describe, expect, it } from "vitest";
import { durationOrDash, pct, seconds, severityTone, statusTone } from "@/lib/format";

describe("pct", () => {
  it("rounds a fraction to a whole percentage", () => {
    expect(pct(0.985)).toBe("99%");
    expect(pct(0.5)).toBe("50%");
  });

  it("shows a dash when there is no rate", () => {
    expect(pct(null)).toBe("—");
  });
});

describe("seconds", () => {
  it("formats to one decimal place", () => {
    expect(seconds(11.858)).toBe("11.9s");
  });

  it("shows a dash when there is no latency", () => {
    expect(seconds(null)).toBe("—");
  });
});

describe("durationOrDash", () => {
  it("measures elapsed time between start and completion", () => {
    expect(durationOrDash("2026-09-25T10:00:00Z", "2026-09-25T10:00:11.5Z")).toBe("11.5s");
  });

  it("shows a dash for a run that has not completed", () => {
    expect(durationOrDash("2026-09-25T10:00:00Z", null)).toBe("—");
  });
});

describe("statusTone", () => {
  it("maps validation and run statuses to tones", () => {
    expect(statusTone("accepted")).toBe("good");
    expect(statusTone("completed")).toBe("good");
    expect(statusTone("rejected")).toBe("bad");
    expect(statusTone("failed")).toBe("bad");
    expect(statusTone("needs_review")).toBe("warn");
    expect(statusTone("running")).toBe("info");
  });

  it("falls back to neutral for unknown statuses", () => {
    expect(statusTone("something_new")).toBe("neutral");
  });
});

describe("severityTone", () => {
  it("escalates tone with severity", () => {
    expect(severityTone("critical")).toBe("bad");
    expect(severityTone("medium")).toBe("warn");
    expect(severityTone("info")).toBe("neutral");
  });
});
