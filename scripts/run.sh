REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

WORKFLOWS="legal_m_and_a" # legal_m_and_a, marketing_campaign, tech_company_acquisition
MODE=assign_all # random, cot, assign_all

uv run python examples/run_examples.py \
  --workflow_name $WORKFLOWS \
  --manager-agent-mode $MODE \
  --model-name gpt-4o-mini \
  --output-dir diagnostics/outputs/$MODE \
  --seed 42