import Link from "next/link";
import { notFound } from "next/navigation";
import { SeverityBadge, StatusBadge } from "@/components/Badge";
import StatCard from "@/components/StatCard";
import { getReviewDetail } from "@/lib/api";

function dateOrDash(s: string | null): string {
  return s ? new Date(s).toLocaleString() : "—";
}

function durationOrDash(started: string, completed: string | null): string {
  if (!completed) return "—";
  const seconds = (new Date(completed).getTime() - new Date(started).getTime()) / 1000;
  return `${seconds.toFixed(1)}s`;
}

export default async function ReviewDetailPage(props: PageProps<"/repositories/[id]/reviews/[reviewId]">) {
  const { id, reviewId } = await props.params;
  const review = await getReviewDetail(reviewId);

  if (!review) {
    notFound();
  }

  return (
    <div className="space-y-6">
      <div>
        <Link href={`/repositories/${id}`} className="text-sm text-blue-600 hover:underline dark:text-blue-400">
          ← {review.repository_full_name}
        </Link>
        <div className="mt-1 flex items-center gap-3">
          <h1 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
            #{review.pr_number} {review.pr_title ?? ""}
          </h1>
          <StatusBadge status={review.status} />
        </div>
        <p className="text-sm text-slate-500">
          {review.pr_author ? `by ${review.pr_author} · ` : ""}
          {review.run_type} review · started {dateOrDash(review.started_at)} · took{" "}
          {durationOrDash(review.started_at, review.completed_at)}
          {review.head_sha ? ` · ${review.head_sha.slice(0, 7)}` : ""}
        </p>
        {review.error_message && (
          <p className="mt-2 rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700 dark:bg-rose-950 dark:text-rose-300">
            {review.error_message}
          </p>
        )}
      </div>

      <div className="grid grid-cols-3 gap-4 sm:grid-cols-6">
        <StatCard label="Files analyzed" value={review.stats.files_analyzed} />
        <StatCard label="Candidates" value={review.stats.candidate_findings} />
        <StatCard label="Accepted" value={review.stats.accepted} />
        <StatCard label="Needs review" value={review.stats.needs_review} />
        <StatCard label="Rejected" value={review.stats.rejected} />
        <StatCard label="Comments posted" value={review.stats.comments_posted} />
      </div>

      <div>
        <h2 className="mb-2 text-sm font-medium text-slate-700 dark:text-slate-300">Findings</h2>
        {review.findings.length === 0 ? (
          <p className="text-sm text-slate-500">No candidate findings for this review.</p>
        ) : (
          <div className="overflow-hidden rounded-lg border border-slate-200 dark:border-slate-800">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-100 text-xs uppercase tracking-wide text-slate-500 dark:bg-slate-900 dark:text-slate-400">
                <tr>
                  <th className="px-4 py-2 font-medium">Severity</th>
                  <th className="px-4 py-2 font-medium">Category</th>
                  <th className="px-4 py-2 font-medium">File</th>
                  <th className="px-4 py-2 font-medium">Score</th>
                  <th className="px-4 py-2 font-medium">Status</th>
                  <th className="px-4 py-2 font-medium">Static</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                {review.findings.map((finding) => (
                  <tr key={finding.id} className="bg-white hover:bg-slate-50 dark:bg-slate-950 dark:hover:bg-slate-900">
                    <td className="px-4 py-2">
                      <SeverityBadge severity={finding.severity} />
                    </td>
                    <td className="px-4 py-2 capitalize text-slate-500">{finding.category}</td>
                    <td className="px-4 py-2">
                      <Link href={`/findings/${finding.id}`} className="font-medium text-blue-600 hover:underline dark:text-blue-400">
                        {finding.title}
                      </Link>
                      <div className="text-xs text-slate-400">
                        {finding.file_path}:{finding.start_line}
                      </div>
                    </td>
                    <td className="px-4 py-2">{finding.validation_score?.toFixed(2) ?? "—"}</td>
                    <td className="px-4 py-2">
                      <StatusBadge status={finding.validation_status} />
                    </td>
                    <td className="px-4 py-2 text-slate-500">{finding.static_corroborated ? "✓" : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
