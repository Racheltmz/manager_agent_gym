import type { DagDiff, DagNode, DiffStatus } from "../api";

export type DagMode = "diff" | "before" | "after";

const W = 176;
const H = 54;
const GAP_X = 64;
const GAP_Y = 20;
const PAD = 20;

const COLOR: Record<DiffStatus, string> = {
  added: "var(--added)",
  removed: "var(--removed)",
  changed: "var(--changed)",
  unchanged: "var(--unchanged)",
};

/** Greedy word wrap into at most `lines` lines, ellipsising the remainder. */
function wrap(text: string, max = 24, lines = 2): string[] {
  const out: string[] = [];
  let cur = "";
  for (const w of text.split(/\s+/)) {
    if ((cur + " " + w).trim().length > max && cur) {
      out.push(cur);
      cur = w;
    } else cur = (cur + " " + w).trim();
  }
  if (cur) out.push(cur);
  if (out.length > lines) {
    const kept = out.slice(0, lines);
    kept[lines - 1] = kept[lines - 1].slice(0, max - 1) + "…";
    return kept;
  }
  return out;
}

const visible = (status: DiffStatus | "added" | "removed" | "unchanged", mode: DagMode) =>
  mode === "diff" || (mode === "before" ? status !== "added" : status !== "removed");

export default function DagView({
  dag,
  mode,
  selected,
  onSelect,
}: {
  dag: DagDiff;
  mode: DagMode;
  selected: string | null;
  onSelect: (id: string | null) => void;
}) {
  const nodes = dag.nodes.filter((n) => visible(n.status, mode));
  const byId = new Map<string, DagNode>(nodes.map((n) => [n.id, n]));
  const pos = (n: DagNode) => ({ x: PAD + n.layer * (W + GAP_X), y: PAD + n.row * (H + GAP_Y) });

  const maxLayer = Math.max(0, ...nodes.map((n) => n.layer));
  const maxRow = Math.max(0, ...nodes.map((n) => n.row));
  const width = PAD * 2 + (maxLayer + 1) * W + maxLayer * GAP_X;
  const height = PAD * 2 + (maxRow + 1) * H + maxRow * GAP_Y;

  return (
    <svg width={width} height={height} onClick={() => onSelect(null)} style={{ display: "block" }}>
      <defs>
        {(["added", "removed", "unchanged"] as const).map((s) => (
          <marker key={s} id={`arrow-${s}`} viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
            <path d="M0,0 L10,5 L0,10 z" fill={COLOR[s]} />
          </marker>
        ))}
      </defs>

      {dag.edges
        .filter((e) => visible(e.status, mode) && byId.has(e.source) && byId.has(e.target))
        .map((e) => {
          const a = pos(byId.get(e.source)!);
          const b = pos(byId.get(e.target)!);
          const x1 = a.x + W, y1 = a.y + H / 2, x2 = b.x, y2 = b.y + H / 2;
          const mid = (x1 + x2) / 2;
          return (
            <path
              key={`${e.source}->${e.target}`}
              d={`M${x1},${y1} C${mid},${y1} ${mid},${y2} ${x2 - 2},${y2}`}
              fill="none"
              stroke={COLOR[e.status]}
              strokeWidth={e.status === "unchanged" ? 1 : 1.8}
              strokeDasharray={e.status === "removed" ? "5 4" : undefined}
              opacity={e.status === "unchanged" ? 0.55 : 0.95}
              markerEnd={`url(#arrow-${e.status})`}
            />
          );
        })}

      {nodes.map((n) => {
        const { x, y } = pos(n);
        const color = COLOR[n.status];
        const lines = wrap(n.id);
        return (
          <g
            key={n.id}
            transform={`translate(${x},${y})`}
            onClick={(ev) => {
              ev.stopPropagation();
              onSelect(n.id);
            }}
            style={{ cursor: "pointer" }}
          >
            <title>{n.id}</title>
            <rect
              width={W}
              height={H}
              rx={8}
              fill="var(--bg)"
              stroke={color}
              strokeWidth={selected === n.id ? 3 : n.status === "unchanged" ? 1 : 2}
              strokeDasharray={n.status === "removed" ? "5 4" : undefined}
            />
            <rect width={5} height={H} rx={2} fill={color} />
            {lines.map((l, i) => (
              <text key={i} x={14} y={22 + i * 15} fontSize={12} fill="var(--text)">
                {l}
              </text>
            ))}
          </g>
        );
      })}
    </svg>
  );
}
