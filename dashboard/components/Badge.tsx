import { severityTone, statusTone, type Tone } from "@/lib/format";

const TONE_STYLES: Record<Tone, string> = {
  good: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300",
  bad: "bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300",
  warn: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
  info: "bg-sky-100 text-sky-800 dark:bg-sky-950 dark:text-sky-300",
  neutral: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
};

function Badge({ text, tone }: { text: string; tone: Tone }) {
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium capitalize ${TONE_STYLES[tone]}`}>
      {text.replace("_", " ")}
    </span>
  );
}

export function StatusBadge({ status }: { status: string }) {
  return <Badge text={status} tone={statusTone(status)} />;
}

export function SeverityBadge({ severity }: { severity: string }) {
  return <Badge text={severity} tone={severityTone(severity)} />;
}
