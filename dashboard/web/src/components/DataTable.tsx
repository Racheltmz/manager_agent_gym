export type Column<T> = { key: keyof T & string; label?: string; digits?: number };

function fmt(v: unknown, digits?: number): string {
  if (v === null || v === undefined) return "–";
  if (typeof v === "boolean") return v ? "yes" : "no";
  if (typeof v === "number") return digits === undefined ? String(v) : v.toFixed(digits);
  return String(v);
}

export default function DataTable<T extends object>({ rows, columns }: { rows: T[]; columns: Column<T>[] }) {
  if (!rows.length) return <div className="muted">No rows.</div>;
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c.key}>{c.label ?? c.key}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>
              {columns.map((c) => {
                const v = (r as Record<string, unknown>)[c.key];
                return (
                  <td key={c.key} className={typeof v === "number" ? "num" : ""}>
                    {fmt(v, c.digits)}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
