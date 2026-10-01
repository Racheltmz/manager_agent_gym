REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Dev: FastAPI on :8000, Vite (hot reload) on :5173. Read-only; never starts a run.
(cd dashboard/web && [ -d node_modules ] || npm install)
uv run uvicorn dashboard.server.main:app --port 8000 --reload &
API_PID=$!
trap 'kill $API_PID 2>/dev/null' EXIT
cd dashboard/web && npm run dev
