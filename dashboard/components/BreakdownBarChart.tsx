"use client";

import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

// A brand-neutral placeholder palette, applied by array position (category/
// severity labels vary per repo, so a fixed name->color map would silently
// miss new labels).
const COLORS = ["#2563eb", "#7c3aed", "#059669", "#d97706", "#dc2626", "#0891b2"];

export default function BreakdownBarChart({
  title,
  data,
}: {
  title: string;
  data: Record<string, number>;
}) {
  const rows = Object.entries(data).map(([name, count]) => ({ name, count }));

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
      <div className="mb-3 text-sm font-medium text-slate-700 dark:text-slate-300">{title}</div>
      {rows.length === 0 ? (
        <div className="flex h-48 items-center justify-center text-sm text-slate-400">No data yet</div>
      ) : (
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={rows} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-slate-200 dark:stroke-slate-800" />
            <XAxis dataKey="name" tick={{ fontSize: 12 }} className="capitalize" />
            <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
            <Tooltip
              contentStyle={{ fontSize: 12, borderRadius: 8 }}
              cursor={{ fill: "rgba(148, 163, 184, 0.15)" }}
            />
            <Bar dataKey="count" radius={[4, 4, 0, 0]}>
              {rows.map((row, i) => (
                <Cell key={row.name} fill={COLORS[i % COLORS.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
