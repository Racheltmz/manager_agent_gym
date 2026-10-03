import { useEffect, useRef, useState } from "react";
import type { Compare, DiffStatus } from "../api";
import GraphView from "./GraphView";

const STATUSES: DiffStatus[] = ["added", "removed", "changed", "unchanged"];

export default function ComparePanes({
  data,
  beforeLabel,
  afterLabel,
  selected,
  onSelect,
}: {
  data: Compare;
  beforeLabel: string;
  afterLabel: string;
  selected: string | null;
  onSelect: (id: string | null) => void;
}) {
  const refs = [useRef<HTMLDivElement>(null), useRef<HTMLDivElement>(null)];
  const syncing = useRef(false);
  const [zoom, setZoom] = useState<"fit" | "100">("fit");
  const [paneWidth, setPaneWidth] = useState(0);

  useEffect(() => {
    const el = refs[0].current;
    if (!el) return;
    const ro = new ResizeObserver(() => setPaneWidth(el.clientWidth));
    ro.observe(el);
    setPaneWidth(el.clientWidth);
    return () => ro.disconnect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // "fit" shrinks the canvas to the pane width, but never below 55% so text stays readable.
  const scale = zoom === "100" || !paneWidth ? 1 : Math.min(1, Math.max(0.55, (paneWidth - 4) / data.canvas.width));

  // Both panes share one layout, so scrolling one scrolls the other to the same spot.
  const sync = (from: number) => () => {
    if (syncing.current) return;
    const src = refs[from].current;
    const dst = refs[1 - from].current;
    if (!src || !dst) return;
    syncing.current = true;
    dst.scrollLeft = src.scrollLeft;
    dst.scrollTop = src.scrollTop;
    requestAnimationFrame(() => (syncing.current = false));
  };

  const detail = selected ? data.details[selected] : null;
  const differences = data.counts.added + data.counts.removed + data.counts.changed;

  return (
    <>
      <div className="legend">
        {STATUSES.map((s) => (
          <span key={s}>
            <i style={{ background: `var(--${s})` }} />
            {s} {data.counts[s]}
          </span>
        ))}
        {differences === 0 && <span>no differences</span>}
        <span className="seg" style={{ marginLeft: "auto" }}>
          {(["fit", "100"] as const).map((z) => (
            <button key={z} className={zoom === z ? "on" : ""} onClick={() => setZoom(z)}>
              {z === "fit" ? "fit" : "100%"}
            </button>
          ))}
        </span>
      </div>

      <div className="compare-grid">
        {([["Before", beforeLabel, data.before], ["After", afterLabel, data.after]] as const).map(([title, label, pane], i) => (
          <div key={title} className="pane">
            <h3>
              {title} <span className="muted">{label}</span>
            </h3>
            <div className="dag-canvas" ref={refs[i]} onScroll={sync(i)}>
              <GraphView
                pane={pane}
                canvas={data.canvas}
                selected={selected}
                onSelect={onSelect}
                id={title.toLowerCase()}
                orientation={data.orientation}
                scale={scale}
              />
            </div>
          </div>
        ))}
      </div>

      {detail && (
        <div className="detail-table">
          <h3>{detail.title}</h3>
          <table>
            <thead>
              <tr>
                <th></th>
                <th>Before</th>
                <th>After</th>
              </tr>
            </thead>
            <tbody>
              {detail.rows.map((r) => (
                <tr key={r.label} className={!r.meta && r.before !== r.after ? "differs" : ""}>
                  <th>{r.label}</th>
                  <td>{r.before ?? "–"}</td>
                  <td>{r.after ?? "–"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
