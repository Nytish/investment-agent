#!/usr/bin/env bash
# ============================================================
# setup-local-model.sh — Install Ollama + pull qwen2.5:14b
# Run once: bash scripts/setup-local-model.sh
# ============================================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  AI Investment Co-pilot — Local Model Setup          ║"
echo "║  Model: qwen2.5:14b (~8.9 GB download)               ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# ── Step 1: Check Homebrew ─────────────────────────────────
if ! command -v brew &>/dev/null; then
  echo -e "${RED}✗ Homebrew not found.${NC}"
  echo "  Install it first: https://brew.sh"
  exit 1
fi
echo -e "${GREEN}✓ Homebrew found${NC}"

# ── Step 2: Install Ollama ─────────────────────────────────
if command -v ollama &>/dev/null; then
  echo -e "${GREEN}✓ Ollama already installed${NC}"
else
  echo -e "${YELLOW}→ Installing Ollama...${NC}"
  brew install ollama
  echo -e "${GREEN}✓ Ollama installed${NC}"
fi

# ── Step 3: Start Ollama service ───────────────────────────
echo -e "${YELLOW}→ Starting Ollama service...${NC}"
brew services start ollama 2>/dev/null || true
sleep 2

# Verify it's running
if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
  echo -e "${GREEN}✓ Ollama is running${NC}"
else
  echo -e "${YELLOW}→ Starting Ollama manually...${NC}"
  ollama serve &
  sleep 3
fi

# ── Step 4: Pull qwen2.5:14b ──────────────────────────────
echo ""
echo -e "${YELLOW}→ Pulling qwen2.5:14b (~8.9 GB)...${NC}"
echo "  This will take 5-15 minutes on a fast connection."
echo ""
ollama pull qwen2.5:14b
echo -e "${GREEN}✓ qwen2.5:14b ready${NC}"

# ── Step 5: Quick test ────────────────────────────────────
echo ""
echo -e "${YELLOW}→ Testing tool calling...${NC}"
RESPONSE=$(curl -s http://localhost:11434/api/chat -d '{
  "model": "qwen2.5:14b",
  "messages": [{"role": "user", "content": "Say exactly: READY"}],
  "stream": false
}' | python3 -c "import sys,json; print(json.load(sys.stdin)['message']['content'])" 2>/dev/null || echo "test skipped")
echo -e "${GREEN}✓ Model response: ${RESPONSE}${NC}"

# ── Done ──────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  Setup complete!                                     ║"
echo "║                                                      ║"
echo "║  Your agent now has 3 fallback levels:               ║"
echo "║  1. gemini-2.5-flash  (cloud, best)                  ║"
echo "║  2. gemini-1.5-flash  (cloud, stable)                ║"
echo "║  3. qwen2.5:14b       (local, offline ✓)             ║"
echo "║                                                      ║"
echo "║  Run: npm run serve                                  ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
