import Link from "next/link";
import { listRepositories } from "@/lib/api";

function pct(n: number | null): string {
  return n === null ? "—" : `${Math.round(n * 100)}%`;
}

function dateOrDash(s: string | null): string {
  return s ? new Date(s).toLocaleString() : "—";
}

export default async function RepositoriesPage() {
  const repos = await listRepositories();

  return (
    <div className="space-y-4">
      <h1 className="text-lg font-semibold text-slate-900 dark:text-slate-100">Repositories</h1>

      {repos.length === 0 ? (
        <p className="text-sm text-slate-500">No repositories reviewed yet.</p>
      ) : (
        <div className="overflow-hidden rounded-lg border border-slate-200 dark:border-slate-800">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-100 text-xs uppercase tracking-wide text-slate-500 dark:bg-slate-900 dark:text-slate-400">
              <tr>
                <th className="px-4 py-2 font-medium">Repository</th>
                <th className="px-4 py-2 font-medium">Default branch</th>
                <th className="px-4 py-2 font-medium">Reviews</th>
                <th className="px-4 py-2 font-medium">Findings</th>
                <th className="px-4 py-2 font-medium">Validation rate</th>
                <th className="px-4 py-2 font-medium">Last review</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
              {repos.map((repo) => (
                <tr key={repo.id} className="bg-white hover:bg-slate-50 dark:bg-slate-950 dark:hover:bg-slate-900">
                  <td className="px-4 py-2">
                    <Link href={`/repositories/${repo.id}`} className="font-medium text-blue-600 hover:underline dark:text-blue-400">
                      {repo.full_name}
                    </Link>
                  </td>
                  <td className="px-4 py-2 text-slate-500">{repo.default_branch ?? "—"}</td>
                  <td className="px-4 py-2">{repo.review_count}</td>
                  <td className="px-4 py-2">{repo.findings_count}</td>
                  <td className="px-4 py-2">{pct(repo.validation_acceptance_rate)}</td>
                  <td className="px-4 py-2 text-slate-500">{dateOrDash(repo.last_review)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
