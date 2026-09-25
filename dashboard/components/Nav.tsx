import Link from "next/link";

export default function Nav() {
  return (
    <header className="border-b border-slate-200 dark:border-slate-800">
      <div className="mx-auto flex max-w-6xl items-center gap-6 px-6 py-4">
        <Link href="/" className="font-semibold tracking-tight">
          DriftWatch
        </Link>
        <nav className="flex gap-4 text-sm text-slate-600 dark:text-slate-400">
          <Link href="/" className="hover:text-slate-900 dark:hover:text-slate-100">
            Overview
          </Link>
          <Link href="/repositories" className="hover:text-slate-900 dark:hover:text-slate-100">
            Repositories
          </Link>
        </nav>
      </div>
    </header>
  );
}
