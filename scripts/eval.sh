#!/usr/bin/env bash
# Analyse existing runs only (reads files, no simulation, no API calls). Same as `scripts/run.sh <benchmark> eval`;
# the settings live in run.sh.
#
#   scripts/eval.sh [original|team]     (default: team)
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/run.sh" "${1:-${BENCHMARK:-team}}" eval
