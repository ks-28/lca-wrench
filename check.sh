#!/bin/zsh
# All checks: lint (ruff) and tests (pytest, in the test project lca-wrench-test).
# The browser tests (Chrome, port 8795) take about a minute; skip them with --no-browser.
cd "$(dirname "$0")"
PY=${PYTHON:-.venv/bin/python}
export PYTHONWARNINGS="ignore::UserWarning,ignore::DeprecationWarning"
ARGS=()
for a in "$@"; do
  if [ "$a" = "--no-browser" ]; then export LCA_WRENCH_SKIP_BROWSER=1; else ARGS+=("$a"); fi
done
$PY -m ruff check . || exit 1
$PY -m pytest -q "${ARGS[@]}"
