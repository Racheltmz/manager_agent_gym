REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

WORKFLOWS="marketing_campaign" # legal_m_and_a, marketing_campaign, orsa
MODE=cot # random, cot, assign_all
# cot = Chain-of-Thought manager

uv run python examples/run_examples.py \
  --workflow_name $WORKFLOWS \
  --manager-agent-mode $MODE \
  --model-name gpt-5 \
  --output-dir dashboard/outputs/$MODE \
  --seed 42