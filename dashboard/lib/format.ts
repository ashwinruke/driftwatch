export function pct(n: number | null): string {
  return n === null ? "—" : `${Math.round(n * 100)}%`;
}

export function seconds(n: number | null): string {
  return n === null ? "—" : `${n.toFixed(1)}s`;
}

export function dateOrDash(s: string | null): string {
  return s ? new Date(s).toLocaleString() : "—";
}

export function durationOrDash(started: string, completed: string | null): string {
  if (!completed) return "—";
  const elapsed = (new Date(completed).getTime() - new Date(started).getTime()) / 1000;
  return `${elapsed.toFixed(1)}s`;
}

export type Tone = "good" | "bad" | "warn" | "info" | "neutral";

const STATUS_TONES: Record<string, Tone> = {
  accepted: "good",
  completed: "good",
  rejected: "bad",
  failed: "bad",
  needs_review: "warn",
  running: "info",
};

const SEVERITY_TONES: Record<string, Tone> = {
  critical: "bad",
  high: "bad",
  medium: "warn",
  low: "info",
  info: "neutral",
};

export function statusTone(status: string): Tone {
  return STATUS_TONES[status] ?? "neutral";
}

export function severityTone(severity: string): Tone {
  return SEVERITY_TONES[severity] ?? "neutral";
}
