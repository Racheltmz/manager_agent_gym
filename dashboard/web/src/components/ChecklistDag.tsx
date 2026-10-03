import { useState } from "react";
import { api, type Run } from "../api";
import { useAsync } from "../useAsync";
import { wrap } from "./GraphView";

const W = 176, H = 60, GX = 64, GY = 16, PAD = 20; // sizes as in the compare page

/** Deterministic checklist score per task, as a DAG; node intensity = score at the chosen timestep. */
export default function ChecklistDag({ runs }: { runs: Run[] }) {
  const [idx, setIdx] = useState(0);
  const [step, setStep] = useState<number | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const run = runs[Math.min(idx, runs.length - 1)];
  const g = useAsync(
    () => (run ? api.checklistDag(run.workflow_folder, run.manager_mode, run.run) : Promise.resolve(null)),
    [run?.workflow_folder, run?.manager_mode, run?.run],
  );
  const dag = g.data;
  const last = dag ? dag.timesteps[dag.timesteps.length - 1] : 0;
  const t = Math.min(step ?? last, last);
  const detail = useAsync(
    () => (run && selected ? api.checklistTask(run.workflow_folder, run.manager_mode, run.run, selected, t) : Promise.resolve(null)),
    [run?.workflow_folder, run?.manager_mode, run?.run, selected, t],
  );
  if (!run) return <div className="muted">No runs.</div>;
  const pos = new Map(dag?.nodes.map((n) => [n.id, { x: PAD + n.layer * (W + GX), y: PAD + n.row * (H + GY) }]));
  const width = dag ? (Math.max(...dag.nodes.map((n) => n.layer)) + 1) * (W + GX) - GX + PAD * 2 : 0;
  const height = dag ? (Math.max(...dag.nodes.map((n) => n.row)) + 1) * (H + GY) - GY + PAD * 2 : 0;

  return (
    <>
      <div className="filters">
        <label>
          Run
          <select value={idx} onChange={(e) => setIdx(Number(e.target.value))}>
            {runs.map((r, i) => (
              <option key={i} value={i}>
                {r.manager_mode} / {r.workflow_folder} / {r.run}
              </option>
            ))}
          </select>
        </label>
        <label>
          Timestep {t}
          <input type="range" min={0} max={last} value={t} onChange={(e) => setStep(Number(e.target.value))} />
        </label>
      </div>
      {g.error && <div className="error">{g.error}</div>}
      {dag && (
        <div className="dag-canvas">
        <svg width={width} height={height} style={{ display: "block" }} onClick={() => setSelected(null)}>
          <defs>
            <marker id="cl-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
              <path d="M0,0 L10,5 L0,10 z" fill="var(--unchanged)" />
            </marker>
          </defs>
          {dag.edges.map(([a, b]) => {
            const p = pos.get(a), q = pos.get(b);
            if (!p || !q) return null;
            const [x1, y1, x2, y2] = [p.x + W, p.y + H / 2, q.x - 2, q.y + H / 2];
            return <path key={a + b} d={`M${x1},${y1} C${(x1 + x2) / 2},${y1} ${(x1 + x2) / 2},${y2} ${x2},${y2}`} fill="none" stroke="var(--unchanged)" opacity={0.55} markerEnd="url(#cl-arrow)" />;
          })}
          {dag.nodes.map((n) => {
            const s = n.scores[String(t)];
            const frac = s && s.total ? s.passed / s.total : 0;
            const p = pos.get(n.id)!;
            const tip = s
              ? `${n.id}\nscore ${s.passed}/${s.total}\nstatus ${s.status}\nagent ${s.agent ?? "-"}\nfailed: ${s.failed_keys.join(", ") || "none"}`
              : `${n.id}\nno output at timestep ${t} (${n.total} checks)`;
            return (
              <g
                key={n.id}
                transform={`translate(${p.x},${p.y})`}
                style={{ cursor: "pointer" }}
                onClick={(e) => {
                  e.stopPropagation();
                  setSelected(n.id);
                }}
              >
                <title>{tip}</title>
                <rect width={W} height={H} rx={8} fill="var(--bg)" stroke="var(--unchanged)" strokeWidth={selected === n.id ? 3 : 1} strokeDasharray={s ? undefined : "5 4"} />
                <rect width={W} height={H} rx={8} fill="var(--added)" fillOpacity={s ? 0.1 + 0.6 * frac : 0} />
                <rect width={5} height={H} rx={2} fill="var(--added)" />
                {wrap(n.id, Math.floor((W - 26) / 6.4)).map((l, i) => (
                  <text key={i} x={14} y={18 + i * 14} fontSize={12} fill="var(--text)">{l}</text>
                ))}
                <text x={14} y={H - 8} fontSize={10.5} fill="var(--muted)">{s ? `${s.passed}/${s.total} checks` : "no output"}</text>
              </g>
            );
          })}
        </svg>
        </div>
      )}
      {selected && (
        <div className="detail-table">
          <h3>
            {selected} <span className="muted">at timestep {t}</span>
          </h3>
          {detail.error && <div className="error">{detail.error}</div>}
          {detail.data?.parts.map((p) => (
            <div key={p.task} style={{ marginBottom: 14 }}>
              <strong>{p.task === selected ? "Task" : "Subtask"}: {p.task}</strong>
              {p.requirements.length > 0 && (
                <table>
                  <thead>
                    <tr><th>Checklist requirement</th><th>Description</th><th>Pattern (regex)</th><th>Result</th></tr>
                  </thead>
                  <tbody>
                    {p.requirements.map((q) => (
                      <tr key={q.key}>
                        <td>{q.key}</td>
                        <td>{q.description}</td>
                        <td><code>{q.pattern}</code></td>
                        <td>{q.passed ? "pass" : "fail"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
              {p.requirements.length > 0 && (
                <div className="muted" style={{ margin: "6px 0" }}>
                  Each pattern is searched in the combined text of all the outputs below. A requirement passes if it matches anywhere in that text.
                </div>
              )}
              <h4 style={{ margin: "10px 0 4px" }}>Outputs</h4>
              {p.outputs.length === 0 && <div className="muted">No output yet.</div>}
              {p.outputs.map((o, i) => (
                <details key={i}>
                  <summary>{o.name ?? "output"}</summary>
                  <pre style={{ whiteSpace: "pre-wrap", maxHeight: 320, overflow: "auto" }}>{o.content}</pre>
                </details>
              ))}
            </div>
          ))}
        </div>
      )}
    </>
  );
}
