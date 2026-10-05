import Link from "next/link";
import { notFound } from "next/navigation";
import StatCard from "@/components/StatCard";
import { EvaluationRunDetail, EvaluationRunSummary, getEvaluationRun, listEvaluationRuns } from "@/lib/api";
import { dateOrDash, pct, seconds } from "@/lib/format";

const METRIC_ROWS: [string, (m: EvaluationRunSummary["before_validation"]) => string][] = [
  ["Precision", (m) => pct(m.precision)],
  ["Recall", (m) => pct(m.recall)],
  ["F1", (m) => pct(m.f1)],
  ["False-positive rate", (m) => pct(m.false_positive_rate)],
];

function MetricsTable({ run }: { run: EvaluationRunSummary }) {
  return (
    <div className="overflow-hidden rounded-lg border border-slate-200 dark:border-slate-800">
      <table className="w-full text-left text-sm">
        <thead className="bg-slate-100 text-xs uppercase tracking-wide text-slate-500 dark:bg-slate-900 dark:text-slate-400">
          <tr>
            <th className="px-4 py-2 font-medium">Metric</th>
            <th className="px-4 py-2 font-medium">Without validation</th>
            <th className="px-4 py-2 font-medium">With validation</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
          {METRIC_ROWS.map(([label, value]) => (
            <tr key={label} className="bg-white dark:bg-slate-950">
              <td className="px-4 py-2">{label}</td>
              <td className="px-4 py-2 text-slate-500">{value(run.before_validation)}</td>
              <td className="px-4 py-2 font-medium">{value(run.after_validation)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function RunDetail({ run }: { run: EvaluationRunDetail }) {
  return (
    <div className="space-y-6">
      <p className="text-sm text-slate-500">
        Run #{run.id} · {run.fixture_count} fixtures · {dateOrDash(run.created_at)}
      </p>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard label="Candidates" value={run.total_candidates} />
        <StatCard label="Accepted" value={run.total_accepted} />
        <StatCard label="Needs review" value={run.total_needs_review} />
        <StatCard label="Rejected" value={run.total_rejected} />
      </div>

      <MetricsTable run={run} />

      <div>
        <h2 className="mb-2 text-sm font-medium text-slate-700 dark:text-slate-300">Per fixture</h2>
        <div className="overflow-hidden rounded-lg border border-slate-200 dark:border-slate-800">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-100 text-xs uppercase tracking-wide text-slate-500 dark:bg-slate-900 dark:text-slate-400">
              <tr>
                <th className="px-4 py-2 font-medium">Fixture</th>
                <th className="px-4 py-2 font-medium">Expected</th>
                <th className="px-4 py-2 font-medium">Accepted</th>
                <th className="px-4 py-2 font-medium">Rejected</th>
                <th className="px-4 py-2 font-medium">Latency</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
              {run.fixtures.map((f) => (
                <tr key={f.fixture} className="bg-white dark:bg-slate-950">
                  <td className="px-4 py-2 font-mono text-xs">{f.fixture}</td>
                  <td className="px-4 py-2">
                    <span className="text-slate-600 dark:text-slate-400">{f.expected ? "Should flag" : "Should stay clean"}</span>
                  </td>
                  <td className="px-4 py-2">{f.accepted_count}</td>
                  <td className="px-4 py-2">{f.rejected_count}</td>
                  <td className="px-4 py-2 text-slate-500">{seconds(f.latency_seconds)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div>
        <h2 className="mb-2 text-sm font-medium text-slate-700 dark:text-slate-300">Known limitations</h2>
        <ul className="list-disc space-y-1 pl-5 text-sm text-slate-600 dark:text-slate-400">
          {run.known_limitations.map((limitation) => (
            <li key={limitation}>{limitation}</li>
          ))}
        </ul>
      </div>
    </div>
  );
}

export default async function EvaluationPage(props: PageProps<"/evaluation">) {
  const { run } = await props.searchParams;
  const runs = await listEvaluationRuns();

  if (runs.length === 0) {
    return (
      <div className="space-y-4">
        <h1 className="text-lg font-semibold text-slate-900 dark:text-slate-100">Evaluation</h1>
        <p className="text-sm text-slate-500">
          No evaluation runs recorded yet. Run <code className="font-mono">python -m driftwatch.cli.evaluate</code>{" "}
          against the database to populate this page.
        </p>
      </div>
    );
  }

  const selectedId = typeof run === "string" ? run : String(runs[0].id);
  const detail = await getEvaluationRun(selectedId);
  if (!detail) {
    notFound();
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold text-slate-900 dark:text-slate-100">Evaluation</h1>
        <div className="flex gap-3 text-sm">
          {runs.map((r) => (
            <Link
              key={r.id}
              href={`/evaluation?run=${r.id}`}
              className={
                r.id === detail.id
                  ? "font-semibold text-slate-900 dark:text-slate-100"
                  : "text-blue-600 hover:underline dark:text-blue-400"
              }
            >
              #{r.id}
            </Link>
          ))}
        </div>
      </div>
      <RunDetail run={detail} />
    </div>
  );
}
