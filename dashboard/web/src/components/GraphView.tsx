import type { DiffStatus, GNode, Pane } from "../api";

const COLOR: Record<DiffStatus, string> = {
  added: "var(--added)",
  removed: "var(--removed)",
  changed: "var(--changed)",
  unchanged: "var(--unchanged)",
};

/** Greedy wrap into at most `lines` lines. Breaks at spaces and after underscores, so long
 *  snake_case names wrap instead of overflowing; the remainder is ellipsised. */
export function wrap(text: string, max: number, lines = 2): string[] {
  const tokens = text.split(/(?<=_)|\s+/).filter(Boolean);
  const out: string[] = [];
  let cur = "";
  for (const tok of tokens) {
    const joined = cur === "" ? tok : cur.endsWith("_") ? cur + tok : cur + " " + tok;
    if (joined.length > max && cur) {
      out.push(cur);
      cur = tok;
    } else cur = joined;
  }
  if (cur) out.push(cur);
  if (out.length > lines) {
    const kept = out.slice(0, lines);
    kept[lines - 1] = kept[lines - 1].slice(0, max - 1) + "…";
    return kept;
  }
  return out.map((l) => (l.length > max ? l.slice(0, max - 1) + "…" : l));
}

const LINE_H = 15;

function Node({ n, selected, onSelect }: { n: GNode; selected: boolean; onSelect: (id: string) => void }) {
  const color = COLOR[n.status];
  const label = wrap(n.label, Math.floor((n.w - 26) / 6.4));
  const labelBase = 18 + (label.length - 1) * 14; // baseline of the last label line
  const subBase = labelBase + 15;
  const linesBase = (n.sublabel ? subBase : labelBase) + 17; // baseline of the first chip line
  let tagX = 14;
  return (
    <g
      transform={`translate(${n.x},${n.y})`}
      onClick={(e) => {
        e.stopPropagation();
        onSelect(n.id);
      }}
      style={{ cursor: "pointer" }}
    >
      <title>{n.label}</title>
      <rect
        width={n.w}
        height={n.h}
        rx={8}
        fill="var(--bg)"
        stroke={color}
        strokeWidth={selected ? 3 : n.status === "unchanged" ? 1 : 2}
        strokeDasharray={n.status === "removed" ? "5 4" : undefined}
      />
      <rect width={5} height={n.h} rx={2} fill={color} />
      {label.map((l, i) => (
        <text key={i} x={14} y={18 + i * 14} fontSize={12} fill="var(--text)">
          {l}
        </text>
      ))}
      {n.sublabel && (
        <text x={14} y={subBase} fontSize={10.5} fill="var(--muted)">
          {n.sublabel}
        </text>
      )}
      {n.lines.map((l, i) => (
        <g key={i} transform={`translate(14,${linesBase + i * LINE_H})`}>
          <circle cx={3} cy={-3.5} r={3} fill={COLOR[l.status]} />
          <text x={12} fontSize={11} fill="var(--text)">
            {l.text}
          </text>
        </g>
      ))}
      {n.tags.map((t) => {
        const w = t.length * 6 + 12;
        const x = tagX;
        tagX += w + 5;
        return (
          <g key={t} transform={`translate(${x},${n.h - 22})`}>
            <rect width={w} height={16} rx={8} fill="var(--panel)" stroke="var(--border)" />
            <text x={w / 2} y={11.5} fontSize={10} textAnchor="middle" fill="var(--muted)">
              {t}
            </text>
          </g>
        );
      })}
    </g>
  );
}

export default function GraphView({
  pane,
  canvas,
  selected,
  onSelect,
  id,
  orientation,
  scale,
}: {
  pane: Pane;
  canvas: { width: number; height: number };
  selected: string | null;
  onSelect: (id: string | null) => void;
  id: string;
  orientation: "horizontal" | "vertical";
  scale: number;
}) {
  const byId = new Map(pane.nodes.map((n) => [n.id, n]));
  return (
    <svg
      width={canvas.width * scale}
      height={canvas.height * scale}
      viewBox={`0 0 ${canvas.width} ${canvas.height}`}
      onClick={() => onSelect(null)}
      style={{ display: "block" }}
    >
      <defs>
        {(["added", "removed", "unchanged"] as const).map((s) => (
          <marker key={s} id={`${id}-arrow-${s}`} viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
            <path d="M0,0 L10,5 L0,10 z" fill={COLOR[s]} />
          </marker>
        ))}
      </defs>
      {pane.edges.map((e) => {
        const a = byId.get(e.source);
        const b = byId.get(e.target);
        if (!a || !b) return null;
        const vertical = orientation === "vertical";
        const [x1, y1] = vertical ? [a.x + a.w / 2, a.y + a.h] : [a.x + a.w, a.y + a.h / 2];
        const [x2, y2] = vertical ? [b.x + b.w / 2, b.y - 2] : [b.x - 2, b.y + b.h / 2];
        const d = vertical
          ? `M${x1},${y1} C${x1},${(y1 + y2) / 2} ${x2},${(y1 + y2) / 2} ${x2},${y2}`
          : `M${x1},${y1} C${(x1 + x2) / 2},${y1} ${(x1 + x2) / 2},${y2} ${x2},${y2}`;
        return (
          <path
            key={`${e.source}->${e.target}`}
            d={d}
            fill="none"
            stroke={COLOR[e.status]}
            strokeWidth={e.status === "unchanged" ? 1 : 1.8}
            strokeDasharray={e.status === "removed" ? "5 4" : undefined}
            opacity={e.status === "unchanged" ? 0.55 : 0.95}
            markerEnd={`url(#${id}-arrow-${e.status})`}
          />
        );
      })}
      {pane.nodes.map((n) => (
        <Node key={n.id} n={n} selected={selected === n.id} onSelect={onSelect} />
      ))}
    </svg>
  );
}
