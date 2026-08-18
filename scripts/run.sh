REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

WORKFLOWS="tech_company_acquisition" # legal_m_and_a, marketing_campaign, tech_company_acquisition, orsa
MODE=cot # random, cot, assign_all

uv run python examples/run_examples.py \
  --workflow_name $WORKFLOWS \
  --manager-agent-mode $MODE \
  --model-name gpt-4o-mini \
  --output-dir diagnostics/outputs/$MODE \
  --seed 42