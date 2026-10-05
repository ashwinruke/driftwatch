export default function Loading() {
  return (
    <div className="animate-pulse space-y-6" aria-busy="true" aria-label="Loading">
      <div className="h-6 w-48 rounded bg-slate-200 dark:bg-slate-800" />
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="h-24 rounded-lg bg-slate-200 dark:bg-slate-800" />
        ))}
      </div>
      <div className="h-64 rounded-lg bg-slate-200 dark:bg-slate-800" />
    </div>
  );
}
