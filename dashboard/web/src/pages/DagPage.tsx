import { useEffect, useMemo, useState } from "react";
import { api, type DagNode, type DiffStatus } from "../api";
import { useAsync } from "../useAsync";
import DagView, { type DagMode } from "../components/DagView";

const STATUSES: DiffStatus[] = ["added", "removed", "changed", "unchanged"];

function Detail({ node }: { node: DagNode }) {
  return (
    <div className="detail">
      <h3>{node.id}</h3>
      <dl style={{ margin: 0 }}>
        <dt>status</dt>
        <dd>
          {node.status}
          {node.changed_fields.length ? ` (${node.changed_fields.join(", ")})` : ""}
        </dd>
        <dt>checklist items (before → after)</dt>
        <dd>
          {node.requirements_before ?? "–"} → {node.requirements_after ?? "–"}
        </dd>
        <dt>subtasks</dt>
        <dd>{node.subtask_count}</dd>
        {node.description_before !== node.description_after && node.description_before && (
          <>
            <dt>description before</dt>
            <dd>{node.description_before}</dd>
          </>
        )}
        {node.description_after && (
          <>
            <dt>description after</dt>
            <dd>{node.description_after}</dd>
          </>
        )}
      </dl>
    </div>
  );
}

export default function DagPage() {
  const scenarios = useAsync(() => api.scenarios(), []);
  const [before, setBefore] = useState("");
  const [after, setAfter] = useState("");
  const [mode, setMode] = useState<DagMode>("diff");
  const [selected, setSelected] = useState<string | null>(null);

  const list = scenarios.data ?? [];

  // Default: the first team-variant scenario against its original of the same name; until one
  // exists, legal_m_and_a (the benchmark's starting scenario) against itself.
  useEffect(() => {
    if (!list.length || before) return;
    const team = list.find((s) => s.collection === "end_to_end_examples_team");
    const base = team ?? list.find((s) => s.name === "legal_m_and_a") ?? list[0];
    const original = list.find((s) => s.collection === "end_to_end_examples" && s.name === base.name) ?? base;
    setBefore(original.id);
    setAfter(base.id);
  }, [list, before]);

  const dag = useAsync(() => (before && after ? api.dagDiff(before, after) : Promise.resolve(null)), [before, after]);
  const node = useMemo(() => dag.data?.nodes.find((n) => n.id === selected) ?? null, [dag.data, selected]);

  const options = (
    <>
      {list.map((s) => (
        <option key={s.id} value={s.id}>
          {s.id}
        </option>
      ))}
    </>
  );

  return (
    <>
      <div className="filters">
        <label>
          Before
          <select value={before} onChange={(e) => setBefore(e.target.value)}>
            {options}
          </select>
        </label>
        <label>
          After
          <select value={after} onChange={(e) => setAfter(e.target.value)}>
            {options}
          </select>
        </label>
        <div className="seg">
          {(["diff", "before", "after"] as DagMode[]).map((m) => (
            <button key={m} className={mode === m ? "on" : ""} onClick={() => setMode(m)}>
              {m}
            </button>
          ))}
        </div>
        {dag.data && (
          <div className="legend">
            {STATUSES.map((s) => (
              <span key={s}>
                <i style={{ background: `var(--${s})` }} />
                {s} {dag.data!.counts[s]}
              </span>
            ))}
          </div>
        )}
      </div>

      {scenarios.error && <div className="error">{scenarios.error}</div>}
      {dag.error && <div className="error">{dag.error}</div>}
      {dag.data && (
        <div className="dag-layout">
          <div className="dag-canvas">
            <DagView dag={dag.data} mode={mode} selected={selected} onSelect={setSelected} />
          </div>
          {node && <Detail node={node} />}
        </div>
      )}
    </>
  );
}
