import BreakdownBarChart from "@/components/BreakdownBarChart";
import StatCard from "@/components/StatCard";
import { getOverview } from "@/lib/api";

function pct(n: number | null): string {
  return n === null ? "—" : `${Math.round(n * 100)}%`;
}

function seconds(n: number | null): string {
  return n === null ? "—" : `${n.toFixed(1)}s`;
}

export default async function OverviewPage() {
  const overview = await getOverview();

  return (
    <div className="space-y-6">
      <h1 className="text-lg font-semibold text-slate-900 dark:text-slate-100">Overview</h1>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
        <StatCard label="Repositories" value={overview.total_repositories} />
        <StatCard label="Review runs" value={overview.total_review_runs} />
        <StatCard label="PRs reviewed" value={overview.total_prs_reviewed} />
        <StatCard label="Total findings" value={overview.total_findings} />
        <StatCard label="Validation acceptance" value={pct(overview.validation_acceptance_rate)} />
        <StatCard label="Avg. review latency" value={seconds(overview.average_review_latency_seconds)} />
      </div>

      <div className="grid grid-cols-3 gap-4 sm:grid-cols-3">
        <StatCard label="Accepted findings" value={overview.accepted_findings} />
        <StatCard label="Needs review" value={overview.needs_review_findings} />
        <StatCard label="Rejected findings" value={overview.rejected_findings} />
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <BreakdownBarChart title="Findings by category" data={overview.findings_by_category} />
        <BreakdownBarChart title="Findings by severity" data={overview.findings_by_severity} />
      </div>
    </div>
  );
}
