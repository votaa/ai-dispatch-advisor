#!/usr/bin/env bash
set -euo pipefail

python3 scripts/init_db.py

echo "Backend setup:"
echo "  cd backend"
echo "  python3 -m venv .venv"
echo "  source .venv/bin/activate"
echo "  pip install -r requirements.txt"
echo "  uvicorn app.main:app --reload"
echo
echo "Frontend setup:"
echo "  cd frontend"
echo "  npm install"
echo "  npm run dev"

