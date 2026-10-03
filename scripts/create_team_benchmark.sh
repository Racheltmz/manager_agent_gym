#!/usr/bin/env bash
# Run the create-team-benchmark skill from the terminal (headless Claude Code).
#
#   scripts/create_team_benchmark.sh legal_m_and_a              create it, or update an existing one in place (only what changed)
#   scripts/create_team_benchmark.sh legal_m_and_a --plan-only  print the plan, write nothing
#   scripts/create_team_benchmark.sh legal_m_and_a --rebuild    delete and recreate it from scratch
#   scripts/create_team_benchmark.sh orsa icap                  several workflows, one Claude run each
#   scripts/create_team_benchmark.sh --stale                    convert every missing or stale workflow
#   scripts/create_team_benchmark.sh --status                   list missing / current / stale workflows
#
# Env: CLAUDE_MODEL=<alias or id> to pick the model. Uses Claude, never the OpenAI API. Gate validation
# (one Claude call per affected task and worker) is deferred; correct_agents is set by judgment.
# Inside an interactive Claude Code session you can run /create-team-benchmark <workflow> instead.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

TOOL="uv run python scripts/team_benchmark.py"

if [ $# -eq 0 ]; then
  sed -n '2,11p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
  exit 1
fi

if [ "$1" = "--status" ]; then
  $TOOL status
  exit 0
fi

PLAN_ONLY=""
REBUILD=""
NAMES=()
for arg in "$@"; do
  case "$arg" in
    --plan-only) PLAN_ONLY="--plan-only" ;;
    --rebuild) REBUILD="--rebuild" ;;
    --stale) while read -r name state _; do
               case "$state" in missing|stale|unstamped) NAMES+=("$name") ;; esac
             done < <($TOOL status | grep -E '^[a-z_0-9]+ +(missing|current|stale|unstamped)') ;;
    -*) echo "unknown option: $arg" >&2; exit 1 ;;
    *) NAMES+=("$arg") ;;
  esac
done

if [ ${#NAMES[@]} -eq 0 ]; then
  echo "nothing to do"
  exit 0
fi

# Headless mode does not expand /slash commands, so ask for the skill in words.
# Edits are auto-accepted; Bash is limited to the tool, the import check, and pytest.
for name in "${NAMES[@]}"; do
  echo "=== create-team-benchmark: $name ${PLAN_ONLY} ${REBUILD} ==="
  claude -p "Use the create-team-benchmark skill with these arguments: ${name} ${PLAN_ONLY} ${REBUILD}. Follow it exactly and end with its report." \
    --permission-mode acceptEdits \
    --allowedTools "Read Write Edit Glob Grep Bash(uv run python scripts/team_benchmark.py *) Bash(uv run python -c *) Bash(uv run pytest *)" \
    ${CLAUDE_MODEL:+--model "$CLAUDE_MODEL"}
done
