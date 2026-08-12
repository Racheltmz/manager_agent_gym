"""
Gradio app to browse diagnostic run results.

Scans diagnostics/outputs/<manager_mode>/<workflow>/run_seed_*/summary.json
(written by diagnostics/analyze_diagnostic_runs.py) and compares manager
modes (cot / random / assign_all) against each other, per workflow, on the
five headline scalar metrics found in each summary.json:

    weighted_preference_total, constraint_adherence, stakeholder_management,
    goal_achievement, workflow_completion_time_hours

It also exposes the richer per-run diagnostic fields that
analyze_diagnostic_runs.py computes (agent join/assignment timeline, failed
tasks handed to just-joined agents, and rubric violations) so a single run
can be drilled into to explain *why* a mode scored the way it did — e.g.
confirming that OneShotDelegateManagerAgent ("assign_all") only assigns
tasks visible at its very first observation and then no-ops forever, so any
agent that joins the team afterward is permanently starved of work.

Usage:
    uv run python diagnostics/eval_app.py
"""

from __future__ import annotations

import json
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
    ax.set_xticklabels(modes)
    ax.set_ylabel("Normalized Score")
    ax2.set_ylabel("Workflow Completion Time (hours)")
    ax.legend(bars, labels, loc="upper left", bbox_to_anchor=(0, 1.15), fontsize=8, ncols=n_metrics)
    ax.spines["top"].set_visible(False)
    ax2.spines["top"].set_visible(False)
    fig.tight_layout()
    return fig

AGENT_JOIN_COLUMNS = [
    "agent_id",
    "join_timestep",
    "join_reason",
    "first_assignment_timestep",
    "assignment_lag",
    "delayed",
    "never_assigned",
    "capabilities_visible_at_join",
]


def load_summaries() -> pd.DataFrame:
    rows = []
    for summary_path in sorted(OUT_ROOT.glob("*/*/run_seed_*/summary.json")):
        try:
            data = json.loads(summary_path.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        row = {
            "workflow": data.get("workflow"),
            "manager_mode": data.get("manager_mode"),
            "run_dir": str(summary_path.parent),
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
        "run_dir",
    ]
    return pd.DataFrame(rows, columns=columns)


def load_run_detail(run_dir: str) -> dict | None:
    if not run_dir:
        return None
    summary_path = Path(run_dir) / "summary.json"
    try:
        return json.loads(summary_path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def refresh():
    df = load_summaries()
    workflows = sorted(df["workflow"].dropna().unique().tolist())
    return df, gr.update(choices=workflows, value=workflows[0] if workflows else None)


def filter_workflow(df: pd.DataFrame, workflow: str | None):
    if df is None or df.empty or not workflow:
        return pd.DataFrame(columns=["manager_mode", *METRICS]), gr.update(choices=[], value=None)
    sub = df[df["workflow"] == workflow].reset_index(drop=True)
    run_choices = [
        f"{row.manager_mode} :: {row.run_dir}" for row in sub.itertuples()
    ]
    display_cols = [
        "manager_mode",
        *METRICS,
        "total_tasks",
        "completed_tasks",
        "failed_tasks",
        "never_assigned_agents",
        "delayed_assignment_agents",
        "rubric_violations",
    ]
    return sub[display_cols], gr.update(choices=run_choices, value=run_choices[0] if run_choices else None)


def run_choice_to_dir(choice: str | None) -> str | None:
    if not choice or " :: " not in choice:
        return None
    return choice.split(" :: ", 1)[1]


def render_run_detail(run_choice: str | None):
    run_dir = run_choice_to_dir(run_choice)
    data = load_run_detail(run_dir) if run_dir else None
    if not data:
        empty = pd.DataFrame(columns=AGENT_JOIN_COLUMNS)
        return "No run selected.", empty, empty, empty

    lines = [
        f"### {data.get('workflow')} — {data.get('manager_mode')}",
        f"`{data.get('run_dir')}`",
        "",
        f"- total_tasks: **{data.get('total_tasks')}**, "
        f"completed: **{data.get('completed_tasks')}**, "
        f"failed: **{data.get('failed_tasks')}**",
        f"- weighted_preference_total: **{data.get('weighted_preference_total')}**, "
        f"constraint_adherence: **{data.get('constraint_adherence')}**, "
        f"stakeholder_management: **{data.get('stakeholder_management')}**, "
        f"goal_achievement: **{data.get('goal_achievement')}**",
        f"- workflow_completion_time_hours: **{data.get('workflow_completion_time_hours')}**",
    ]
    for note in data.get("notes", []):
        lines.append(f"- note: {note}")
    summary_md = "\n".join(lines)

    joins = pd.DataFrame(data.get("agent_join_analyses", []), columns=AGENT_JOIN_COLUMNS)
    if not joins.empty:
        # Surface the agents most likely to explain a bad score first.
        joins = joins.sort_values(
            by=["never_assigned", "delayed", "join_timestep"], ascending=[False, False, True]
        ).reset_index(drop=True)

    failed_recent = pd.DataFrame(
        data.get("failed_tasks_assigned_to_recent_joiners", []),
        columns=["task_id", "assigned_agent_id", "agent_join_timestep"],
    )

    violations = pd.DataFrame(
        data.get("rubric_violations", []), columns=["name", "score", "max_score", "error"]
    )

    return summary_md, joins, failed_recent, violations


with gr.Blocks(title="Manager Agent Gym — Eval Dashboard") as demo:
    gr.Markdown("# Manager Agent Gym — Diagnostic Run Comparison")
    gr.Markdown(
        "Loads every `summary.json` under `diagnostics/outputs/<mode>/<workflow>/run_seed_*/` "
        "(regenerate with `uv run python diagnostics/analyze_diagnostic_runs.py`) and compares "
        "manager modes on the 5 headline metrics, plus per-run agent-assignment diagnostics."
    )

    state_df = gr.State(pd.DataFrame())

    with gr.Row():
        reload_btn = gr.Button("Reload summaries", variant="primary")
        workflow_dropdown = gr.Dropdown(label="Benchmark (workflow)", choices=[], interactive=True)

    table = gr.Dataframe(label="Metrics by manager mode", interactive=False)

    # gr.BarPlot only stacks when a color column is used (no grouped/dodged
    # bar support in this Gradio build), so this is a plain matplotlib figure
    # instead — one combined chart with all 5 metrics grouped per mode,
    # colored to match the reference benchmark figure's legend.
    combined_plot = gr.Plot(label="Metrics by manager mode")

    all_table = gr.Dataframe(label="All runs", interactive=False)

    gr.Markdown("## Run detail — why did this run score the way it did?")
    gr.Markdown(
        "Pick a specific run below. `never_assigned` agents are team members the manager "
        "never gave a single task to; for `assign_all` this typically means everyone who "
        "joined *after* its one-shot assignment at the first observation, since it no-ops "
        "for the rest of the episode."
    )
    run_dropdown = gr.Dropdown(label="Run (mode :: run_dir)", choices=[], interactive=True)
    run_summary_md = gr.Markdown()
    agent_join_table = gr.Dataframe(
        label="Agent join / first-assignment timeline (sorted worst-first)",
        interactive=False,
    )
    failed_recent_table = gr.Dataframe(
        label="Failed tasks assigned to recently-joined agents", interactive=False
    )
    violations_table = gr.Dataframe(label="Rubric violations", interactive=False)

    def on_reload():
        df, dd_update = refresh()
        return df, dd_update, df

    reload_btn.click(on_reload, outputs=[state_df, workflow_dropdown, all_table])
    demo.load(on_reload, outputs=[state_df, workflow_dropdown, all_table])

    def on_workflow_change(df, workflow):
        sub, run_dd_update = filter_workflow(df, workflow)
        figure = make_combined_figure(sub)
        return (sub, figure, run_dd_update)

    workflow_dropdown.change(
        on_workflow_change,
        inputs=[state_df, workflow_dropdown],
        outputs=[table, combined_plot, run_dropdown],
    )

    run_dropdown.change(
        render_run_detail,
        inputs=[run_dropdown],
        outputs=[run_summary_md, agent_join_table, failed_recent_table, violations_table],
    )

if __name__ == "__main__":
    demo.launch()
