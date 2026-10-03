# Analyse existing runs (reads files only, no simulation).
#
#   scripts/eval.sh                 original benchmark: run summaries
#   scripts/eval.sh team            team benchmark: run summaries and the team-change metrics
#   BENCHMARK=team scripts/eval.sh  same, from the environment
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

BENCHMARK="${1:-${BENCHMARK:-original}}" # original, team
case "$BENCHMARK" in original|team) ;; *) echo "BENCHMARK must be 'original' or 'team', got '$BENCHMARK'" >&2; exit 1 ;; esac

WORKFLOWS="marketing_campaign" # original: legal_m_and_a, marketing_campaign, tech_company_acquisition, orsa. team: legal_m_and_a
MODES="cot" # random, cot, assign_all (team: cot, random)
SEED=42

if [ "$BENCHMARK" = "team" ]; then
  LABELS=""
  for wf in $WORKFLOWS; do LABELS="$LABELS ${wf}_team"; done
else
  LABELS="$WORKFLOWS"
fi

uv run python dashboard/analysis/analyze_runs.py \
  --workflow $LABELS \
  --mode $MODES \
  --seed $SEED

if [ "$BENCHMARK" = "team" ]; then
  uv run python dashboard/analysis/analyze_team_changes.py \
    --workflow $LABELS \
    --mode $MODES \
    --seed $SEED
fi
