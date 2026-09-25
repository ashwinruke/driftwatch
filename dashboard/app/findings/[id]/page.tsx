import Link from "next/link";
import { notFound } from "next/navigation";
import { SeverityBadge, StatusBadge } from "@/components/Badge";
import { getFindingDetail } from "@/lib/api";

const EVIDENCE_LABELS: Record<string, string> = {
  diff: "Diff",
  ast: "AST",
  semgrep: "Semgrep",
  bandit: "Bandit",
  gitleaks: "Gitleaks",
  llm: "LLM",
};

function ScoreRow({ label, value }: { label: string; value: number | null }) {
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-slate-500">{label}</span>
      <span className="font-medium text-slate-900 dark:text-slate-100">{value === null ? "—" : value.toFixed(2)}</span>
    </div>
  );
}

export default async function FindingDetailPage(props: PageProps<"/findings/[id]">) {
  const { id } = await props.params;
  const finding = await getFindingDetail(id);

  if (!finding) {
    notFound();
  }

  return (
    <div className="max-w-3xl space-y-6">
      <div>
        <Link
          href={`/repositories/${finding.repository_id}/reviews/${finding.review_run_id}`}
          className="text-sm text-blue-600 hover:underline dark:text-blue-400"
        >
          ← Back to review
        </Link>
        <div className="mt-1 flex items-center gap-3">
          <h1 className="text-lg font-semibold text-slate-900 dark:text-slate-100">{finding.title}</h1>
          <SeverityBadge severity={finding.severity} />
          <StatusBadge status={finding.validation_status} />
        </div>
        <p className="text-sm text-slate-500">
          {finding.category} · {finding.file_path}:{finding.start_line}
          {finding.end_line !== finding.start_line ? `-${finding.end_line}` : ""}
        </p>
      </div>

      <section>
        <h2 className="mb-1 text-sm font-medium text-slate-700 dark:text-slate-300">Issue</h2>
        <p className="text-sm text-slate-600 dark:text-slate-400">{finding.description}</p>
      </section>

      {finding.suggested_fix && (
        <section>
          <h2 className="mb-1 text-sm font-medium text-slate-700 dark:text-slate-300">Suggested fix</h2>
          <pre className="overflow-x-auto rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs dark:border-slate-800 dark:bg-slate-900">
            {finding.suggested_fix}
          </pre>
        </section>
      )}

      <section>
        <h2 className="mb-2 text-sm font-medium text-slate-700 dark:text-slate-300">Evidence</h2>
        {finding.evidence.length === 0 ? (
          <p className="text-sm text-slate-500">No evidence recorded.</p>
        ) : (
          <ul className="space-y-1 text-sm">
            {finding.evidence.map((e, i) => (
              <li key={i} className="flex gap-2 text-slate-600 dark:text-slate-400">
                <span className="w-20 shrink-0 font-medium text-slate-900 dark:text-slate-100">
                  {EVIDENCE_LABELS[e.source] ?? e.source}
                </span>
                <span>
                  {e.description}
                  {e.file_path && e.start_line ? ` (${e.file_path}:${e.start_line})` : ""}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section>
        <h2 className="mb-2 text-sm font-medium text-slate-700 dark:text-slate-300">Validation</h2>
        {finding.validation_breakdown ? (
          <div className="space-y-1.5 rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
            <ScoreRow label="Diff evidence" value={finding.validation_breakdown.diff_evidence} />
            <ScoreRow label="Static analysis" value={finding.validation_breakdown.static_corroboration} />
            <ScoreRow label="AST / location consistency" value={finding.validation_breakdown.ast_consistency} />
            <ScoreRow label="LLM confidence" value={finding.validation_breakdown.llm_confidence} />
            <div className="mt-2 flex items-center justify-between border-t border-slate-200 pt-2 text-sm font-semibold dark:border-slate-800">
              <span>Final validation score</span>
              <span>{finding.validation_breakdown.final_score.toFixed(2)}</span>
            </div>
          </div>
        ) : (
          <div className="rounded-lg border border-slate-200 bg-white p-4 text-sm text-slate-500 dark:border-slate-800 dark:bg-slate-900">
            Pass-through validation (documentation findings are verified by the doc-drift matching workflow
            itself — no four-signal breakdown to show). Score: {finding.validation_score?.toFixed(2) ?? "—"}
          </div>
        )}
      </section>

      {finding.comment?.github_url && (
        <a
          href={finding.comment.github_url}
          target="_blank"
          rel="noreferrer"
          className="inline-block text-sm text-blue-600 hover:underline dark:text-blue-400"
        >
          View comment on GitHub →
        </a>
      )}
    </div>
  );
}
