# Run one workflow with one manager mode.
#
#   scripts/run.sh                 original benchmark (examples/end_to_end_examples)
#   scripts/run.sh team            team-membership benchmark (examples/end_to_end_examples_team)
#   BENCHMARK=team scripts/run.sh  same, from the environment
#
# Team runs are labelled <workflow>_team, so they never overwrite the original runs.
# Calls the OpenAI API (manager gpt-5-mini, workers gpt-5-mini, stakeholder gpt-5.4-mini; LLM-judge rubrics are skipped for team runs).
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

BENCHMARK="${1:-${BENCHMARK:-team}}" # original, team
case "$BENCHMARK" in original|team) ;; *) echo "BENCHMARK must be 'original' or 'team', got '$BENCHMARK'" >&2; exit 1 ;; esac

WORKFLOWS="legal_m_and_a" # original: legal_m_and_a, marketing_campaign, orsa. team: legal_m_and_a
MODE=cot # random, cot, assign_all (team: cot or random; assign_all is excluded)

uv run python examples/run_examples.py \
  --benchmark $BENCHMARK \
  --workflow_name $WORKFLOWS \
  --manager-agent-mode $MODE \
  --model-name gpt-5-mini \
  --output-dir dashboard/outputs/$MODE \
  --seed 42
