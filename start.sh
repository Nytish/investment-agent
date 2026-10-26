#!/bin/bash
# INMarket — start the investment agent
# Usage: ./start.sh

set -e

# Check .env exists
if [ ! -f ".env" ]; then
  echo "❌  .env not found. Copy .env.example and add your GEMINI_API_KEY:"
  echo "    cp .env.example .env"
  exit 1
fi

# Check GEMINI_API_KEY is set
source .env 2>/dev/null || true
if [ -z "$GEMINI_API_KEY" ] || [ "$GEMINI_API_KEY" = "your-gemini-api-key-here" ]; then
  echo "❌  GEMINI_API_KEY not set in .env"
  echo "    Get a free key at https://aistudio.google.com/app/apikey"
  exit 1
fi

# Install dependencies if needed
if ! python -c "import fastapi" 2>/dev/null; then
  echo "📦  Installing dependencies…"
  pip install -r requirements.txt --break-system-packages -q
fi

echo "🚀  Starting INMarket on http://localhost:8000"
python main.py
