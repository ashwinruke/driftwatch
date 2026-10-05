export default async function LoginPage(props: PageProps<"/login">) {
  const { error } = await props.searchParams;
  const demoPassword = process.env.DEMO_PASSWORD;

  return (
    <div className="mx-auto max-w-sm space-y-4 pt-16">
      <h1 className="text-lg font-semibold text-slate-900 dark:text-slate-100">DriftWatch dashboard</h1>
      {error && <p className="text-sm text-rose-600 dark:text-rose-400">Incorrect password.</p>}
      <form action="/api/login" method="post" className="space-y-3">
        <input
          type="password"
          name="password"
          required
          autoFocus
          placeholder="Dashboard password"
          className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900"
        />
        <button type="submit" className="w-full rounded-md bg-slate-900 px-3 py-2 text-sm font-medium text-white dark:bg-slate-100 dark:text-slate-900">
          Sign in
        </button>
      </form>
      {demoPassword && (
        <p className="rounded-md bg-slate-100 px-3 py-2 text-sm text-slate-700 dark:bg-slate-900 dark:text-slate-300">
          Demo access password: <code className="font-mono font-semibold">{demoPassword}</code>
        </p>
      )}
    </div>
  );
}
