#!/usr/bin/env bash
# CareerOS local dev starter
# Loads secrets from backend/.env, then starts backend + frontend.
# Run with: ./dev.sh

set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"

# ── Load .env so system env overrides don't win ──────────────────────────────
ENV_FILE="$ROOT/backend/.env"
if [ ! -f "$ENV_FILE" ]; then
  echo "ERROR: $ENV_FILE not found"
  exit 1
fi

# Export each non-comment line from .env, overriding any existing system env var
while IFS= read -r line || [ -n "$line" ]; do
  [[ "$line" =~ ^#.*$ || -z "$line" ]] && continue
  key="${line%%=*}"
  val="${line#*=}"
  export "$key=$val"
done < "$ENV_FILE"

# ── Start backend ─────────────────────────────────────────────────────────────
echo "▶ Starting backend on :8001"
cd "$ROOT/backend"
.venv/bin/uvicorn app.main:app --port 8001 --reload &
BACKEND_PID=$!

# ── Start frontend ────────────────────────────────────────────────────────────
echo "▶ Starting frontend on :3002"
cd "$ROOT/frontend"
npm run dev -- --port 3002 &
FRONTEND_PID=$!

echo ""
echo "  Backend  → http://localhost:8001"
echo "  Frontend → http://localhost:3002"
echo ""
echo "  Press Ctrl+C to stop both"

# ── Cleanup on exit ───────────────────────────────────────────────────────────
trap "echo ''; echo 'Stopping...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM

wait
