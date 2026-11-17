#!/bin/zsh
# Starts LCA Wrench locally and opens it in Chrome.
cd "$(dirname "$0")"
PORT=${PORT:-8787}
if [ ! -x .venv/bin/python ]; then
  echo "Set it up first: see README.md (venv and setup_daten.py)."; exit 1
fi
if lsof -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "LCA Wrench is already running: http://127.0.0.1:$PORT"
  open -a "Google Chrome" "http://127.0.0.1:$PORT" 2>/dev/null || open "http://127.0.0.1:$PORT"
  exit 0
fi
# bw2calc warns about an optional solver and about empty methods; both are harmless here
export PYTHONWARNINGS="ignore::UserWarning:bw2calc,ignore::UserWarning:bw2calc.lca"
echo "LCA Wrench starts on http://127.0.0.1:$PORT"
echo "The first build takes a few seconds. Stop with Ctrl+C."
( sleep 2; open -a "Google Chrome" "http://127.0.0.1:$PORT" 2>/dev/null || open "http://127.0.0.1:$PORT" ) &
exec .venv/bin/python -m uvicorn lca_wrench.api:app --host 127.0.0.1 --port "$PORT" --log-level warning
