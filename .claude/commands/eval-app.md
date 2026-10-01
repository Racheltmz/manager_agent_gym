---
description: Start or stop the eval dashboard (React + FastAPI)
argument-hint: start | stop (default: start)
---

# Eval dashboard: ${1:-start}

The dashboard only reads existing files under `dashboard/outputs/` and scenario `workflow.py`
files. It never calls the OpenAI API, so starting and stopping it is safe.

If the argument is `stop`, follow **Stop**. Otherwise (empty or `start`) follow **Start**. Any
other argument: say the two valid options and do nothing.

## Start

1. Check whether it is already up: `curl -s -o /dev/null -w "%{http_code}" http://localhost:5173`
   and the same for `http://localhost:8000/api/runs`. If both return 200, skip to step 3.
2. Otherwise run `scripts/launch_dashboard.sh` with `run_in_background: true` (it blocks while
   serving). Then poll both URLs above until they return 200, for at most about 30 seconds. On
   the first run it installs `dashboard/web/node_modules`, which can take a minute. If a port is
   already taken by something else, say so and stop rather than killing that process.
3. Reply with one line: the dashboard URL, `http://localhost:5173`. Mention that `/eval-app stop`
   shuts it down.

## Stop

1. Find the listeners: `lsof -nP -iTCP:5173 -iTCP:8000 -sTCP:LISTEN`. If there are none, reply
   that it is not running.
2. For each listening PID, check its command line (`ps -o command= -p <pid>`). Only kill it if it
   is the dashboard: it contains `dashboard.server.main` (uvicorn) or `dashboard/web` (vite). Leave
   anything else running and say which port is used by something else.
3. Also stop the background `scripts/launch_dashboard.sh` task if this session started one, so the
   launcher does not keep running with nothing behind it.
4. Confirm both ports no longer respond, then reply with one line saying it is stopped.
