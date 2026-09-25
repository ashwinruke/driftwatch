import Link from "next/link";
import { notFound } from "next/navigation";
import { StatusBadge } from "@/components/Badge";
import StatCard from "@/components/StatCard";
import { getRepositoryDetail } from "@/lib/api";

function dateOrDash(s: string | null): string {
  return s ? new Date(s).toLocaleString() : "—";
}

export default async function RepositoryDetailPage(props: PageProps<"/repositories/[id]">) {
  const { id } = await props.params;
  const repo = await getRepositoryDetail(id);

  if (!repo) {
    notFound();
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-slate-900 dark:text-slate-100">{repo.full_name}</h1>
        <p className="text-sm text-slate-500">Default branch: {repo.default_branch ?? "—"}</p>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <StatCard label="Total reviews" value={repo.total_reviews} />
        <StatCard label="Total findings" value={repo.total_findings} />
        <StatCard label="Last review" value={dateOrDash(repo.last_review)} />
      </div>

      <div>
        <h2 className="mb-2 text-sm font-medium text-slate-700 dark:text-slate-300">Recent review runs</h2>
        {repo.recent_reviews.length === 0 ? (
          <p className="text-sm text-slate-500">No review runs yet.</p>
        ) : (
          <div className="overflow-hidden rounded-lg border border-slate-200 dark:border-slate-800">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-100 text-xs uppercase tracking-wide text-slate-500 dark:bg-slate-900 dark:text-slate-400">
                <tr>
                  <th className="px-4 py-2 font-medium">PR</th>
                  <th className="px-4 py-2 font-medium">Type</th>
                  <th className="px-4 py-2 font-medium">Status</th>
                  <th className="px-4 py-2 font-medium">Started</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                {repo.recent_reviews.map((run) => (
                  <tr key={run.id} className="bg-white hover:bg-slate-50 dark:bg-slate-950 dark:hover:bg-slate-900">
                    <td className="px-4 py-2">
                      <Link
                        href={`/repositories/${repo.id}/reviews/${run.id}`}
                        className="font-medium text-blue-600 hover:underline dark:text-blue-400"
                      >
                        #{run.pr_number} {run.pr_title ?? ""}
                      </Link>
                    </td>
                    <td className="px-4 py-2 capitalize text-slate-500">{run.run_type}</td>
                    <td className="px-4 py-2">
                      <StatusBadge status={run.status} />
                    </td>
                    <td className="px-4 py-2 text-slate-500">{dateOrDash(run.started_at)}</td>
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
