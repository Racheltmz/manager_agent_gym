REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

WORKFLOWS="marketing_campaign" # legal_m_and_a, marketing_campaign, tech_company_acquisition, orsa
MODES="cot" # random, cot, assign_all
SEED=42

uv run python dashboard/analysis/analyze_runs.py \
  --workflow $WORKFLOWS \
  --mode $MODES \
  --seed $SEED
