"""
Gradio app to browse diagnostic run results.

Scans diagnostics/outputs/<manager_mode>/<workflow>/run_seed_*/summary.json
(written by diagnostics/analyze_diagnostic_runs.py) and compares manager
modes (cot / random / assign_all) against each other, per workflow, on the
five headline scalar metrics found in each summary.json:

    weighted_preference_total, constraint_adherence, stakeholder_management,
    goal_achievement, workflow_completion_time_hours

It also aggregates the richer per-run diagnostic fields that
analyze_diagnostic_runs.py computes (agent join/assignment timeline, failed
tasks handed to just-joined agents) across every run_seed_* of the selected
workflow, to compare how well each manager mode copes with team-membership
non-stationarity — agents joining the team mid-episode — e.g. confirming
that OneShotDelegateManagerAgent ("assign_all") only assigns tasks visible
at its very first observation and then no-ops forever, so any agent that
joins the team afterward is permanently starved of work.

Usage:
    uv run python diagnostics/eval_app.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import gradio as gr
import matplotlib.pyplot as plt
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_ROOT = REPO_ROOT / "diagnostics" / "outputs"

METRICS = [
    "weighted_preference_total",
    "constraint_adherence",
    "stakeholder_management",
    "goal_achievement",
    "workflow_completion_time_hours",
]

# Display name + color per metric, matching the reference benchmark figure's
# legend (blue/orange/red/green/purple, in that order).
METRIC_STYLE: dict[str, tuple[str, str]] = {
    "weighted_preference_total": ("Preference Alignment", "#1f77b4"),
    "constraint_adherence": ("Constraint Adherence", "#ff7f0e"),
    "stakeholder_management": ("Stakeholder Management", "#d62728"),
    "goal_achievement": ("Goal Achievement", "#2ca02c"),
    "workflow_completion_time_hours": ("Workflow Completion Time (hrs)", "#9467bd"),
}

MODE_ORDER = ["random", "cot", "assign_all"]

# workflow_completion_time_hours lives on its own right-hand axis (hours),
# same as "Workflow Completion Time" in the reference benchmark figure —
# everything else is a normalized 0-1 score sharing the left axis.
RIGHT_AXIS_METRIC = "workflow_completion_time_hours"


def make_combined_figure(df: pd.DataFrame, metrics: list[str] = METRICS):
    """One grouped (dodged) bar chart: x=manager_mode, one bar per metric per
    mode, with the completion-time metric plotted against a secondary right
    axis since it's in hours rather than a normalized 0-1 score."""
    fig, ax = plt.subplots(figsize=(11, 4.5))
    ax2 = ax.twinx()
    if df is None or df.empty:
        ax.set_axis_off()
        return fig

    modes = [m for m in MODE_ORDER if m in set(df["manager_mode"])]
    n_metrics = len(metrics)
    bar_width = 0.8 / max(n_metrics, 1)
    x_positions = range(len(modes))

    bars, labels = [], []
    for i, metric in enumerate(metrics):
        label, color = METRIC_STYLE[metric]
        values = [
            df.loc[df["manager_mode"] == mode, metric].iloc[0]
            if mode in set(df["manager_mode"])
            else None
            for mode in modes
        ]
        values = [v if v is not None else 0 for v in values]
        offsets = [x + (i - (n_metrics - 1) / 2) * bar_width for x in x_positions]
        target_ax = ax2 if metric == RIGHT_AXIS_METRIC else ax
        bar = target_ax.bar(offsets, values, width=bar_width, label=label, color=color)
        bars.append(bar)
        labels.append(label)

    ax.set_xticks(list(x_positions))
    ax.set_xticklabels(modes, fontsize=12)
    ax.set_ylabel("Normalized Score", fontsize=12)
    ax2.set_ylabel("Workflow Completion Time (hours)", fontsize=12)
    ax.legend(bars, labels, loc="upper left", bbox_to_anchor=(0, 1.15), fontsize=8, ncols=n_metrics)
    ax.spines["top"].set_visible(False)
    ax2.spines["top"].set_visible(False)
    fig.tight_layout()
    return fig


# --- Team-membership non-stationarity analysis -----------------------------
#
# analyze_diagnostic_runs.py writes, per run, an "agent_join_analyses" list
# (one entry per agent that joins the team, with its join timestep, its
# first-assignment timestep/lag, and whether it was ever assigned or
# "delayed") plus "failed_tasks_assigned_to_recent_joiners". The functions
# below flatten those per-run lists across every run_seed_* directory so we
# can compare manager modes on how well they cope with agents joining the
# team mid-episode, rather than only inspecting one run at a time.

AGENT_JOIN_FIELDS = [
    "agent_id",
    "join_timestep",
    "join_reason",
    "first_assignment_timestep",
    "assignment_lag",
    "delayed",
    "never_assigned",
    "capabilities_visible_at_join",
]

JOIN_COLUMNS = ["workflow", "manager_mode", "run_dir", *AGENT_JOIN_FIELDS]

FAILED_RECENT_COLUMNS = [
    "workflow",
    "manager_mode",
    "run_dir",
    "task_id",
    "assigned_agent_id",
    "agent_join_timestep",
]

NONSTATIONARITY_AGG_COLUMNS = [
    "manager_mode",
    "agents_tracked",
    "never_assigned_agents",
    "delayed_assignment_agents",
    "avg_assignment_lag_timesteps",
    "capability_gap_at_join",
    "failed_tasks_recent_joiners",
    "rubric_violations",
]

NONSTATIONARITY_METRICS = [
    ("never_assigned_agents", "Never Assigned", "#d62728"),
    ("delayed_assignment_agents", "Delayed Assignment", "#ff7f0e"),
    ("failed_tasks_recent_joiners", "Failed Tasks (Recent Joiners)", "#9467bd"),
    ("capability_gap_at_join", "Capability Gap at Join", "#7f7f7f"),
]


def make_nonstationarity_figure(agg_df: pd.DataFrame):
    """Grouped bar chart: x=manager_mode, one bar per non-stationarity
    metric, summed across every run_seed_* of the selected workflow."""
    fig, ax = plt.subplots(figsize=(11, 4.5))
    if agg_df is None or agg_df.empty:
        ax.set_axis_off()
        return fig

    modes = [m for m in MODE_ORDER if m in set(agg_df["manager_mode"])]
    n_metrics = len(NONSTATIONARITY_METRICS)
    bar_width = 0.8 / max(n_metrics, 1)
    x_positions = range(len(modes))

    bars, labels = [], []
    for i, (col, label, color) in enumerate(NONSTATIONARITY_METRICS):
        values = [
            agg_df.loc[agg_df["manager_mode"] == mode, col].iloc[0]
            if mode in set(agg_df["manager_mode"])
            else 0
            for mode in modes
        ]
        values = [v if pd.notna(v) else 0 for v in values]
        offsets = [x + (i - (n_metrics - 1) / 2) * bar_width for x in x_positions]
        bar = ax.bar(offsets, values, width=bar_width, label=label, color=color)
        bars.append(bar)
        labels.append(label)

    ax.set_xticks(list(x_positions))
    ax.set_xticklabels(modes, fontsize=12)
    ax.set_ylabel("Count (summed across runs)", fontsize=12)
    ax.legend(bars, labels, loc="upper left", bbox_to_anchor=(0, 1.15), fontsize=8, ncols=n_metrics)
    ax.spines["top"].set_visible(False)
    fig.tight_layout()
    return fig


# --- Run health check -------------------------------------------------
#
# A run's output files reflect whatever got written to disk, which doesn't
# by itself distinguish "the manager mode genuinely finished/stalled early"
# from "the process was interrupted/crashed mid-run and never got further"
# — both look like a short timestep_results list. This classifies each run
# from data that already exists on disk (no rerun needed) using
# execution_summary.workflow_completed plus the task backlog
# (pending+ready+running) at the last recorded timestep:
#
#   complete          - workflow_completed is True
#   exhausted         - not complete, but no backlog left (nothing more to do)
#   truncated         - not complete, backlog > 0, and it stopped within
#                        TRUNCATED_TIMESTEP_THRESHOLD timesteps — the
#                        signature of an interrupted/crashed run (this is
#                        what caught assign_all/legal_m_and_a/run_seed_42's
#                        stray 2-timestep rerun mixed in with a stale
#                        50-timestep run's leftover files)
#   in_progress_long  - not complete, backlog > 0, ran a normal number of
#                        timesteps — just didn't finish within budget, which
#                        is legitimate data, not a broken run
#   missing_data      - final_metrics.json unreadable/absent

TRUNCATED_TIMESTEP_THRESHOLD = 3

RUN_HEALTH_FIELDS = [
    "run_status",
    "total_timesteps_recorded",
    "workflow_completed",
    "final_backlog",
    "manager_actions_logged",
]


def check_run_health(run_dir: str) -> dict:
    """Reads a single run's timestep_data/final_metrics.json (+ its
    execution_log, for context) and classifies it per RUN_HEALTH_FIELDS."""
    empty = {
        "run_status": "missing_data",
        "total_timesteps_recorded": None,
        "workflow_completed": None,
        "final_backlog": None,
        "manager_actions_logged": None,
    }
    metrics_path = Path(run_dir) / "timestep_data" / "final_metrics.json"
    try:
        metrics = json.loads(metrics_path.read_text())
    except (json.JSONDecodeError, OSError):
        return empty

    exec_summary = metrics.get("execution_summary") or {}
    workflow_completed = bool(exec_summary.get("workflow_completed"))
    total_timesteps = exec_summary.get("total_timesteps")

    timestep_results = metrics.get("timestep_results") or []
    final_backlog = None
    if timestep_results:
        mo = (timestep_results[-1].get("metadata") or {}).get("manager_observation") or {}
        counts = mo.get("task_status_counts") or {}
        final_backlog = counts.get("pending", 0) + counts.get("ready", 0) + counts.get("running", 0)

    dir_name = Path(run_dir).name  # "run_seed_42" -> run_id "seed_42"
    run_id = dir_name[len("run_"):] if dir_name.startswith("run_") else None
    manager_actions_logged = None
    if run_id:
        log_path = Path(run_dir) / "execution_logs" / f"execution_log_{run_id}.json"
        try:
            log = json.loads(log_path.read_text())
            manager_actions_logged = len(log.get("manager_actions") or [])
        except (json.JSONDecodeError, OSError):
            pass

    if workflow_completed:
        status = "complete"
    elif final_backlog == 0:
        status = "exhausted"
    elif total_timesteps is not None and total_timesteps <= TRUNCATED_TIMESTEP_THRESHOLD:
        status = "truncated"
    else:
        status = "in_progress_long"

    return {
        "run_status": status,
        "total_timesteps_recorded": total_timesteps,
        "workflow_completed": workflow_completed,
        "final_backlog": final_backlog,
        "manager_actions_logged": manager_actions_logged,
    }


def load_summaries() -> pd.DataFrame:
    rows = []
    for summary_path in sorted(OUT_ROOT.glob("*/*/run_seed_*/summary.json")):
        try:
            data = json.loads(summary_path.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        run_dir = str(summary_path.parent)
        row = {
            "workflow": data.get("workflow"),
            "manager_mode": data.get("manager_mode"),
            "run_dir": run_dir,
        }
        for metric in METRICS:
            row[metric] = data.get(metric)
        row["total_tasks"] = data.get("total_tasks")
        row["completed_tasks"] = data.get("completed_tasks")
        row["failed_tasks"] = data.get("failed_tasks")
        never_assigned = sum(
            1 for a in data.get("agent_join_analyses", []) if a.get("never_assigned")
        )
        delayed = sum(1 for a in data.get("agent_join_analyses", []) if a.get("delayed"))
        row["never_assigned_agents"] = never_assigned
        row["delayed_assignment_agents"] = delayed
        row["rubric_violations"] = len(data.get("rubric_violations", []))
        row.update(check_run_health(run_dir))
        rows.append(row)
    columns = [
        "workflow",
        "manager_mode",
        *METRICS,
        "total_tasks",
        "completed_tasks",
        "failed_tasks",
        "never_assigned_agents",
        "delayed_assignment_agents",
        "rubric_violations",
        *RUN_HEALTH_FIELDS,
        "run_dir",
    ]
    return pd.DataFrame(rows, columns=columns)


def load_join_details() -> pd.DataFrame:
    """Flattens agent_join_analyses across every run into one long table,
    tagged with workflow/manager_mode/run_dir so it can be grouped/filtered."""
    rows = []
    for summary_path in sorted(OUT_ROOT.glob("*/*/run_seed_*/summary.json")):
        try:
            data = json.loads(summary_path.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        workflow = data.get("workflow")
        manager_mode = data.get("manager_mode")
        run_dir = str(summary_path.parent)
        for a in data.get("agent_join_analyses", []):
            rows.append(
                {
                    "workflow": workflow,
                    "manager_mode": manager_mode,
                    "run_dir": run_dir,
                    **{field: a.get(field) for field in AGENT_JOIN_FIELDS},
                }
            )
    return pd.DataFrame(rows, columns=JOIN_COLUMNS)


def load_failed_recent_joiners() -> pd.DataFrame:
    """Flattens failed_tasks_assigned_to_recent_joiners across every run."""
    rows = []
    for summary_path in sorted(OUT_ROOT.glob("*/*/run_seed_*/summary.json")):
        try:
            data = json.loads(summary_path.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        workflow = data.get("workflow")
        manager_mode = data.get("manager_mode")
        run_dir = str(summary_path.parent)
        for f in data.get("failed_tasks_assigned_to_recent_joiners", []):
            rows.append(
                {
                    "workflow": workflow,
                    "manager_mode": manager_mode,
                    "run_dir": run_dir,
                    "task_id": f.get("task_id"),
                    "assigned_agent_id": f.get("assigned_agent_id"),
                    "agent_join_timestep": f.get("agent_join_timestep"),
                }
            )
    return pd.DataFrame(rows, columns=FAILED_RECENT_COLUMNS)


def make_nonstationarity_agg(
    joins_df: pd.DataFrame,
    failed_df: pd.DataFrame,
    summaries_df: pd.DataFrame,
    workflow: str | None,
    mid_episode_only: bool = False,
) -> pd.DataFrame:
    """Per-manager-mode aggregate of the non-stationarity signals, summed/
    averaged across every run_seed_* of the given workflow.

    create_team_timeline() encodes the initial team as "add" events at
    timestep 0 alongside genuine mid-episode joins, so agent_join_analyses
    (and this aggregate) includes both by default. Set mid_episode_only=True
    to restrict to agents with join_timestep > 0 — i.e. actual team churn,
    not baseline utilization of the starting roster — which is the
    apples-to-apples non-stationarity comparison."""
    if joins_df is None or joins_df.empty or not workflow:
        return pd.DataFrame(columns=NONSTATIONARITY_AGG_COLUMNS)

    j = joins_df[joins_df["workflow"] == workflow]
    if mid_episode_only:
        j = j[j["join_timestep"] > 0]
    f = (
        failed_df[failed_df["workflow"] == workflow]
        if failed_df is not None and not failed_df.empty
        else pd.DataFrame(columns=FAILED_RECENT_COLUMNS)
    )
    s = (
        summaries_df[summaries_df["workflow"] == workflow]
        if summaries_df is not None and not summaries_df.empty
        else pd.DataFrame()
    )

    rows = []
    for mode in [m for m in MODE_ORDER if m in set(j["manager_mode"])]:
        jm = j[j["manager_mode"] == mode]
        lag = jm["assignment_lag"].dropna()
        rows.append(
            {
                "manager_mode": mode,
                "agents_tracked": int(len(jm)),
                "never_assigned_agents": int(jm["never_assigned"].sum()),
                "delayed_assignment_agents": int(jm["delayed"].sum()),
                "avg_assignment_lag_timesteps": round(lag.mean(), 2) if not lag.empty else None,
                "capability_gap_at_join": int((jm["capabilities_visible_at_join"] == False).sum()),  # noqa: E712
                "failed_tasks_recent_joiners": int(len(f[f["manager_mode"] == mode])),
                "rubric_violations": int(s.loc[s["manager_mode"] == mode, "rubric_violations"].sum())
                if not s.empty
                else 0,
            }
        )
    return pd.DataFrame(rows, columns=NONSTATIONARITY_AGG_COLUMNS)


# --- Single-run timestep timeline -------------------------------------------
#
# Each run's timestep_data/final_metrics.json has one entry per timestep with
# a manager_observation.task_status_counts snapshot (pending/ready/running/
# completed/failed) and an agent_coordination_changes list of "Added <id>:
# <reason>" / "Removed <id>: <reason>" strings (as well as unrelated
# "Removed task <uuid>" entries when a task is cancelled/superseded, which
# this regex deliberately excludes since it requires the id token to be
# followed by ": "). Together these let us plot task-status + team-size
# trends over the episode with vertical markers at each join/removal.

AGENT_EVENT_RE = re.compile(r"^(Added|Removed) (?!task )(\S+):\s*(.*)$")

RUN_TIMELINE_COLUMNS = [
    "timestep",
    "pending",
    "ready",
    "running",
    "completed",
    "failed",
    "team_size",
    "workflow_progress_pct",
]

RUN_EVENT_COLUMNS = ["timestep", "event", "agent_id", "reason"]

TIMELINE_METRICS = [
    ("pending", "Pending", "#7f7f7f"),
    ("ready", "Ready", "#17becf"),
    ("running", "Running", "#ff7f0e"),
    ("completed", "Completed", "#2ca02c"),
    ("failed", "Failed", "#d62728"),
    ("team_size", "Team Size", "#1f77b4"),
]


def load_run_timeline(run_dir: str | None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Reads a single run's timestep_data/final_metrics.json into a
    (timeline_df, events_df) pair: task-status/team-size counts per timestep,
    and agent join/removal events per timestep."""
    if not run_dir:
        return (
            pd.DataFrame(columns=RUN_TIMELINE_COLUMNS),
            pd.DataFrame(columns=RUN_EVENT_COLUMNS),
        )
    metrics_path = Path(run_dir) / "timestep_data" / "final_metrics.json"
    try:
        data = json.loads(metrics_path.read_text())
    except (json.JSONDecodeError, OSError):
        return (
            pd.DataFrame(columns=RUN_TIMELINE_COLUMNS),
            pd.DataFrame(columns=RUN_EVENT_COLUMNS),
        )

    rows, events = [], []
    for tr in data.get("timestep_results", []):
        md = tr.get("metadata") or {}
        ts = md.get("timestep")
        mo = md.get("manager_observation") or {}
        counts = mo.get("task_status_counts") or {}
        rows.append(
            {
                "timestep": ts,
                "pending": counts.get("pending", 0),
                "ready": counts.get("ready", 0),
                "running": counts.get("running", 0),
                "completed": counts.get("completed", 0),
                "failed": counts.get("failed", 0),
                "team_size": len(mo.get("agent_ids") or []),
                "workflow_progress_pct": round((mo.get("workflow_progress") or 0) * 100, 1),
            }
        )
        for change in md.get("agent_coordination_changes") or []:
            m = AGENT_EVENT_RE.match(change)
            if not m:
                continue
            action, agent_id, reason = m.groups()
            events.append(
                {
                    "timestep": ts,
                    "event": "joined" if action == "Added" else "removed",
                    "agent_id": agent_id,
                    "reason": reason,
                }
            )

    timeline_df = pd.DataFrame(rows, columns=RUN_TIMELINE_COLUMNS)
    if not timeline_df.empty:
        timeline_df = timeline_df.sort_values("timestep").reset_index(drop=True)
    events_df = pd.DataFrame(events, columns=RUN_EVENT_COLUMNS)
    return timeline_df, events_df


def make_run_timeline_figure(timeline_df: pd.DataFrame, events_df: pd.DataFrame):
    """Multi-line timeline: task-status counts + team size on the left axis,
    workflow-progress % on the right axis, with a plain dotted vertical
    line at every timestep where an agent joined (green) or was removed
    (red) — see run_events_table for which agent(s)."""
    fig, ax = plt.subplots(figsize=(11, 5))
    ax2 = ax.twinx()
    if timeline_df is None or timeline_df.empty:
        ax.set_axis_off()
        return fig

    for col, label, color in TIMELINE_METRICS:
        ax.plot(
            timeline_df["timestep"], timeline_df[col],
            marker="o", markersize=4, label=label, color=color,
        )
    ax2.plot(
        timeline_df["timestep"], timeline_df["workflow_progress_pct"],
        marker="s", markersize=4, linestyle="--",
        label="Workflow Progress (%)", color="#9467bd",
    )

    join_labeled = removed_labeled = False
    if events_df is not None and not events_df.empty:
        for ts, grp in events_df.groupby("timestep"):
            ts = float(ts)
            joined = grp[grp["event"] == "joined"]
            removed = grp[grp["event"] == "removed"]
            if not joined.empty:
                ax.axvline(
                    ts, color="#2ca02c", linestyle=":", alpha=0.7, linewidth=1.5,
                    label=None if join_labeled else "Agent(s) joined",
                )
                join_labeled = True
            if not removed.empty:
                ax.axvline(
                    ts, color="#d62728", linestyle=":", alpha=0.7, linewidth=1.5,
                    label=None if removed_labeled else "Agent(s) removed",
                )
                removed_labeled = True

    ax.set_xlabel("Timestep", fontsize=12)
    ax.set_ylabel("Count", fontsize=12)
    ax2.set_ylabel("Workflow Progress (%)", fontsize=12)
    ax.set_xticks(sorted(timeline_df["timestep"].unique()))

    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(
        lines1 + lines2, labels1 + labels2,
        loc="upper left", bbox_to_anchor=(0, 1.3), fontsize=8, ncols=4,
    )
    ax.spines["top"].set_visible(False)
    ax2.spines["top"].set_visible(False)
    fig.tight_layout()
    return fig


def run_choice_to_dir(choice: str | None) -> str | None:
    if not choice or " :: " not in choice:
        return None
    return choice.split(" :: ", 1)[1]


def list_run_choices(df: pd.DataFrame, workflow: str | None) -> list[str]:
    if df is None or df.empty or not workflow:
        return []
    sub = df[df["workflow"] == workflow]
    return [f"{row.manager_mode} :: {row.run_dir}" for row in sub.itertuples()]


def refresh():
    df = load_summaries()
    joins_df = load_join_details()
    failed_df = load_failed_recent_joiners()
    workflows = sorted(df["workflow"].dropna().unique().tolist())
    dd_update = gr.update(choices=workflows, value=workflows[0] if workflows else None)
    return df, joins_df, failed_df, dd_update


def filter_workflow(df: pd.DataFrame, workflow: str | None) -> pd.DataFrame:
    if df is None or df.empty or not workflow:
        return pd.DataFrame(columns=["manager_mode", *METRICS])
    sub = df[df["workflow"] == workflow].reset_index(drop=True)
    display_cols = [
        "manager_mode",
        "run_status",
        *METRICS,
        "total_tasks",
        "completed_tasks",
        "failed_tasks",
        "never_assigned_agents",
        "delayed_assignment_agents",
        "rubric_violations",
        "run_dir",
    ]
    return sub[display_cols]


with gr.Blocks(title="Manager Agent Gym — Eval Dashboard") as demo:
    gr.Markdown("# Manager Agent Gym — Diagnostic Run Comparison")
    gr.Markdown(
        "Loads every `summary.json` under `diagnostics/outputs/<mode>/<workflow>/run_seed_*/` "
        "(regenerate with `uv run python diagnostics/analyze_diagnostic_runs.py`) and compares "
        "manager modes on the 5 headline metrics, plus aggregated agent-assignment diagnostics."
    )

    # NB: seed these with None, not an empty DataFrame — Gradio's dev-reload
    # watcher (swap_blocks) diffs each component's stored .value across
    # reloads via `==`, and a DataFrame's `==` returns an elementwise frame
    # rather than a bool, which blows up deep_equal's truthiness check on
    # every hot-reload. Every consumer below already treats `None` the same
    # as an empty frame (`df is None or df.empty`).
    state_df = gr.State(None)
    joins_state = gr.State(None)
    failed_state = gr.State(None)

    with gr.Row():
        reload_btn = gr.Button("Reload summaries", variant="primary")
        workflow_dropdown = gr.Dropdown(label="Benchmark (workflow)", choices=[], interactive=True)

    table = gr.Dataframe(label="Metrics by manager mode", interactive=False)

    # gr.BarPlot only stacks when a color column is used (no grouped/dodged
    # bar support in this Gradio build), so this is a plain matplotlib figure
    # instead — one combined chart with all 5 metrics grouped per mode,
    # colored to match the reference benchmark figure's legend.
    combined_plot = gr.Plot(label="Metrics by manager mode")

    gr.Markdown("## Team Membership Non-Stationarity Analysis")
    gr.Markdown(
        "Agents join the team mid-episode (see each scenario's "
        "`create_team_timeline()`); these panels show how well each manager "
        "mode copes with that, aggregated across every `run_seed_*` of the "
        "selected workflow."
    )
    gr.Markdown(
        "- **Never assigned** = the agent got zero tasks all episode.\n"
        "- **Delayed assignment** = its first assignment came several timesteps after it joined.\n"
        "- **Capability gap at join** = the manager's own state snapshot didn't yet expose the agent's capabilities at its join timestep.\n"
        "- **Failed tasks (recent joiners)** = tasks that failed while assigned to one of these agents"
    )
    mid_episode_only_checkbox = gr.Checkbox(
        label="Mid-episode joiners only (join_timestep > 0) — exclude the starting roster",
        value=True,
        info=(
            "create_team_timeline() encodes the initial team as joins at "
            "t=0 too, so unchecked this mixes baseline utilization with "
            "actual churn. Check this for the apples-to-apples "
            "non-stationarity comparison."
        ),
    )
    nonstationarity_plot = gr.Plot(label="Non-stationarity handling by manager mode")
    nonstationarity_table = gr.Dataframe(
        label="Aggregated non-stationarity stats by manager mode", interactive=False
    )

    gr.Markdown("### Agent join / first-assignment timeline (all runs, sorted worst-first)")
    join_timeline_table = gr.Dataframe(interactive=False)

    gr.Markdown("### Failed tasks assigned to recently-joined agents (all runs)")
    failed_recent_table = gr.Dataframe(interactive=False)

    gr.Markdown("## Run Timeline: Task Status & Team Membership Over Time")
    gr.Markdown(
        "Pick a single run to see task-status counts (pending/ready/running/"
        "completed/failed) and team size plotted per timestep, with a "
        "workflow-progress % line on the right axis. Dotted green/red "
        "vertical lines mark timesteps where an agent joined or was "
        "removed, labeled with the agent id(s) — use this to see whether a "
        "roster change (e.g. specialists joining mid-deal) lines up with a "
        "stall, a burst of completions, or a failure spike."
    )
    run_dropdown = gr.Dropdown(label="Run (mode :: run_dir)", choices=[], interactive=True)
    run_timeline_plot = gr.Plot(label="Task status & team size timeline")
    run_events_table = gr.Dataframe(
        label="Agent join/removal events", interactive=False, max_height=400
    )

    def on_reload():
        df, joins_df, failed_df, dd_update = refresh()
        return df, joins_df, failed_df, dd_update

    reload_btn.click(
        on_reload, outputs=[state_df, joins_state, failed_state, workflow_dropdown]
    )
    demo.load(on_reload, outputs=[state_df, joins_state, failed_state, workflow_dropdown])

    def on_workflow_change(df, joins_df, failed_df, workflow, mid_episode_only):
        sub = filter_workflow(df, workflow)
        figure = make_combined_figure(sub)

        agg = make_nonstationarity_agg(joins_df, failed_df, df, workflow, mid_episode_only)
        ns_figure = make_nonstationarity_figure(agg)

        if joins_df is not None and not joins_df.empty and workflow:
            wf_joins = joins_df[joins_df["workflow"] == workflow]
            if mid_episode_only:
                wf_joins = wf_joins[wf_joins["join_timestep"] > 0]
            wf_joins = wf_joins.sort_values(
                by=["never_assigned", "delayed", "manager_mode", "join_timestep"],
                ascending=[False, False, True, True],
            ).reset_index(drop=True)
        else:
            wf_joins = pd.DataFrame(columns=JOIN_COLUMNS)

        if failed_df is not None and not failed_df.empty and workflow:
            wf_failed = failed_df[failed_df["workflow"] == workflow]
            if mid_episode_only:
                wf_failed = wf_failed[wf_failed["agent_join_timestep"] > 0]
            wf_failed = wf_failed.reset_index(drop=True)
        else:
            wf_failed = pd.DataFrame(columns=FAILED_RECENT_COLUMNS)

        run_choices = list_run_choices(df, workflow)
        run_dd_update = gr.update(choices=run_choices, value=run_choices[0] if run_choices else None)

        return sub, figure, ns_figure, agg, wf_joins, wf_failed, run_dd_update

    workflow_dropdown.change(
        on_workflow_change,
        inputs=[state_df, joins_state, failed_state, workflow_dropdown, mid_episode_only_checkbox],
        outputs=[
            table,
            combined_plot,
            nonstationarity_plot,
            nonstationarity_table,
            join_timeline_table,
            failed_recent_table,
            run_dropdown,
        ],
    )

    mid_episode_only_checkbox.change(
        on_workflow_change,
        inputs=[state_df, joins_state, failed_state, workflow_dropdown, mid_episode_only_checkbox],
        outputs=[
            table,
            combined_plot,
            nonstationarity_plot,
            nonstationarity_table,
            join_timeline_table,
            failed_recent_table,
            run_dropdown,
        ],
    )

    def on_run_change(run_choice):
        run_dir = run_choice_to_dir(run_choice)
        timeline_df, events_df = load_run_timeline(run_dir)
        figure = make_run_timeline_figure(timeline_df, events_df)
        return figure, events_df

    run_dropdown.change(
        on_run_change,
        inputs=[run_dropdown],
        outputs=[run_timeline_plot, run_events_table],
    )

if __name__ == "__main__":
    demo.launch()
