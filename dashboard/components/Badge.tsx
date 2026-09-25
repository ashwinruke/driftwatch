const STATUS_STYLES: Record<string, string> = {
  accepted: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300",
  rejected: "bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300",
  needs_review: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
  completed: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300",
  failed: "bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300",
  running: "bg-sky-100 text-sky-800 dark:bg-sky-950 dark:text-sky-300",
};

const SEVERITY_STYLES: Record<string, string> = {
  critical: "bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300",
  high: "bg-orange-100 text-orange-800 dark:bg-orange-950 dark:text-orange-300",
  medium: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
  low: "bg-sky-100 text-sky-800 dark:bg-sky-950 dark:text-sky-300",
  info: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
};

function Badge({ text, styles }: { text: string; styles: Record<string, string> }) {
  const className = styles[text] ?? "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300";
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium capitalize ${className}`}>
      {text.replace("_", " ")}
    </span>
  );
}

export function StatusBadge({ status }: { status: string }) {
  return <Badge text={status} styles={STATUS_STYLES} />;
}

export function SeverityBadge({ severity }: { severity: string }) {
  return <Badge text={severity} styles={SEVERITY_STYLES} />;
}
