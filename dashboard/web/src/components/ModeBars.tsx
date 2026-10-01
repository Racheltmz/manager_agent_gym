import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export type Series = { key: string; label: string; color: string };

/** One bar per manager mode (single series) or grouped bars (several series). */
export default function ModeBars({
  data,
  series,
  height = 170,
  digits = 2,
}: {
  data: Record<string, string | number | null>[];
  series: Series[];
  height?: number;
  digits?: number;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 6, right: 6, bottom: 0, left: -16 }}>
        <CartesianGrid stroke="var(--border)" vertical={false} />
        <XAxis dataKey="manager_mode" tick={{ fill: "var(--muted)", fontSize: 11 }} stroke="var(--border)" />
        <YAxis tick={{ fill: "var(--muted)", fontSize: 11 }} stroke="var(--border)" />
        <Tooltip
          contentStyle={{ background: "var(--bg)", border: "1px solid var(--border)", fontSize: 12 }}
          formatter={(v: number) => (typeof v === "number" ? v.toFixed(digits) : v)}
        />
        {series.map((s) => (
          <Bar key={s.key} dataKey={s.key} name={s.label} fill={s.color} radius={[3, 3, 0, 0]} isAnimationActive={false} />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}
