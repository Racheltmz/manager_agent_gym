#!/usr/bin/env bash
# Run one workflow with one manager mode, then analyse the run. One place for the settings, so
# the run and its analysis always point at the same folder.
#
#   scripts/run.sh [original|team] [all|run|eval]
#
#   scripts/run.sh                 team benchmark (default), run then analyse
#   scripts/run.sh original        original benchmark (examples/end_to_end_examples)
#   scripts/run.sh team eval       analyse an existing run only (free: reads files, no API calls)
#   scripts/run.sh team run        run only (no analysis)
#   BENCHMARK=original STAGE=eval scripts/run.sh   same, from the environment
#   EVAL_MODES="cot random" scripts/run.sh team eval   compare several modes that were already run
#
# Stages: `run` calls the OpenAI API (manager gpt-5-mini, workers gpt-5-mini, stakeholder
# gpt-5.4-mini; LLM-judge rubrics are skipped for team runs). `eval` only reads and writes files:
# run summaries (analyze_runs.py) and, for team runs, the team-change metrics
# (analyze_team_changes.py). `all` runs `run` and then `eval`, and skips `eval` if `run` fails.
# Team runs are labelled <workflow>_team, so they never overwrite the original runs.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# EDIT THESE
BENCHMARK="${BENCHMARK:-team}" # original, team
STAGE="${STAGE:-all}"          # all, run, eval


for arg in "$@"; do
  case "$arg" in
    original|team) BENCHMARK="$arg" ;;
    all|run|eval) STAGE="$arg" ;;
    *) echo "usage: scripts/run.sh [original|team] [all|run|eval]" >&2; exit 1 ;;
  esac
done
case "$BENCHMARK" in original|team) ;; *) echo "BENCHMARK must be 'original' or 'team', got '$BENCHMARK'" >&2; exit 1 ;; esac
case "$STAGE" in all|run|eval) ;; *) echo "STAGE must be 'all', 'run' or 'eval', got '$STAGE'" >&2; exit 1 ;; esac


# EDIT THESE
WORKFLOWS="legal_m_and_a" # original: legal_m_and_a, marketing_campaign, orsa. team: legal_m_and_a
MODE=cot                  # random, cot, assign_all (team: cot or random; assign_all is excluded)
SEED=42
EVAL_MODES="${EVAL_MODES:-$MODE}" # modes to analyse; defaults to the mode that was run

if [ "$BENCHMARK" = "team" ]; then
  LABELS=""
  for wf in $WORKFLOWS; do LABELS="$LABELS ${wf}_team"; done
else
  LABELS="$WORKFLOWS"
fi

if [ "$STAGE" = "all" ] || [ "$STAGE" = "run" ]; then
  uv run python examples/run_examples.py \
    --benchmark "$BENCHMARK" \
    --workflow_name $WORKFLOWS \
    --manager-agent-mode "$MODE" \
    --model-name gpt-5-mini \
    --output-dir "dashboard/outputs/$MODE" \
    --seed "$SEED"
fi

if [ "$STAGE" = "all" ] || [ "$STAGE" = "eval" ]; then
  uv run python dashboard/analysis/analyze_runs.py \
    --workflow $LABELS \
    --mode $EVAL_MODES \
    --seed "$SEED"

  if [ "$BENCHMARK" = "team" ]; then
    uv run python dashboard/analysis/analyze_team_changes.py \
      --workflow $LABELS \
      --mode $EVAL_MODES \
      --seed "$SEED"
  fi
fi
