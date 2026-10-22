#!/bin/bash
# APEX 2.0 — Launch Streamlit Dashboard
# Usage: ./run_dashboard.sh
# Opens at http://localhost:8501

cd "$(dirname "$0")"

# Load .env if it exists
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

streamlit run web/apex_dashboard.py \
  --server.port 8501 \
  --server.headless true \
  --theme.base dark \
  --theme.primaryColor "#00C850"
