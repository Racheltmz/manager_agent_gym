#!/usr/bin/env bash
# Diagnostic suite: team-based non-stationarity / open ad-hoc teamwork.
#
# Runs the 3 churn-heavy scenarios (legal_m_and_a, marketing_campaign,
# tech_company_acquisition) against the 3 baseline manager modes
# (cot, random, assign_all) using gpt-4o-mini via OpenAI, with a fixed seed
# for cross-condition comparability.
#
# All team timelines already exist in the scenario modules
# (examples/end_to_end_examples/<scenario>/team.py) via create_team_timeline(),
# so no new team-composition code is required — this script only drives
# examples/run_examples.py, which already wires create_team_timeline() output
# into AgentRegistry.schedule_agent_add/remove().
#
# Usage:
#   OPENAI_API_KEY=sk-... ./diagnostics/run_diagnostic_suite.sh
# or populate .env at repo root with OPENAI_API_KEY=... beforehand.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

WORKFLOWS=(legal_m_and_a marketing_campaign tech_company_acquisition)
MODES=(cot random assign_all)
MODEL_NAME="gpt-4o-mini"
SEED=42
MAX_TIMESTEPS="${MAX_TIMESTEPS:-}"   # leave empty to use each scenario's natural length / default (50)
OUT_ROOT="diagnostics/outputs"

if [[ -z "${OPENAI_API_KEY:-}" ]] && ! grep -q '^OPENAI_API_KEY=.\+' .env 2>/dev/null; then
  echo "ERROR: OPENAI_API_KEY is not set (env var) and .env has no non-empty OPENAI_API_KEY=... entry." >&2
  echo "Set it before running, e.g.: export OPENAI_API_KEY=sk-..." >&2
  exit 1
fi

mkdir -p "$OUT_ROOT/logs"

TIMESTEP_ARGS=()
if [[ -n "$MAX_TIMESTEPS" ]]; then
  TIMESTEP_ARGS=(--max-timesteps "$MAX_TIMESTEPS")
fi

for mode in "${MODES[@]}"; do
  for wf in "${WORKFLOWS[@]}"; do
    echo "==== workflow=$wf manager_mode=$mode model=$MODEL_NAME seed=$SEED ===="
    RUN_DIR="$OUT_ROOT/$mode/$wf/run_seed_$SEED"
    if [[ -d "$RUN_DIR" ]]; then
      echo "Clearing existing run directory: $RUN_DIR"
      rm -rf "$RUN_DIR"
    fi
    LOG_FILE="$OUT_ROOT/logs/${wf}__${mode}.log"
    python examples/run_examples.py \
      --workflow_name "$wf" \
      --manager-agent-mode "$mode" \
      --model-name "$MODEL_NAME" \
      --output-dir "$OUT_ROOT/$mode" \
      --seed "$SEED" \
      "${TIMESTEP_ARGS[@]}" \
      2>&1 | tee "$LOG_FILE"
  done
done

echo
echo "All 9 runs complete. Outputs under: $OUT_ROOT/<manager_mode>/<workflow_name>/run_<timestamp>/"
echo "Next: python diagnostics/analyze_diagnostic_runs.py"
