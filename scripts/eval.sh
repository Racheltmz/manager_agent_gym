REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

WORKFLOWS="legal_m_and_a" # legal_m_and_a, marketing_campaign, tech_company_acquisition
MODES="assign_all" # random, cot, assign_all
SEED=42

uv run python diagnostics/analyze_diagnostic_runs.py \
  --workflow $WORKFLOWS \
  --mode $MODES \
  --seed $SEED
