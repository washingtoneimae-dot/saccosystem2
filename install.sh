#!/bin/bash
# SACCO System Installer — checks deps, sets everything up

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "=============================="
echo " SACCO Member Statement System"
echo "=============================="
echo ""

# ── Python ──
echo -n "Checking Python... "
PY_VER=$(python3 --version 2>&1 | grep -oP '\d+\.\d+')
PY_MAJOR=$(echo $PY_VER | cut -d. -f1)
PY_MINOR=$(echo $PY_VER | cut -d. -f2)

if [ "$PY_MAJOR" -ge 3 ] && [ "$PY_MINOR" -ge 7 ]; then
    echo -e "${GREEN}✓${NC} Python $PY_VER"
else
    echo -e "${RED}✗${NC} Python 3.7+ required (found $PY_VER)"
    exit 1
fi

# ── Python stdlib modules ──
echo -n "Checking Python modules... "
python3 -c "
import sys, json, uuid, os, subprocess, tempfile, base64, traceback
from datetime import datetime
from http.server import ThreadingHTTPServer
import zipfile, xml.etree.ElementTree, io, threading, sqlite3
print('ok')
" 2>&1 || {
    echo -e "${RED}✗${NC} Missing Python module"
    exit 1
}

# ── Himalaya ──
echo -n "Checking Himalaya CLI... "
HIM_VER=$(himalaya --version 2>&1 | grep -oP 'v[\d\.]+' | head -1 || echo "")
if [ -n "$HIM_VER" ]; then
    echo -e "${GREEN}✓${NC} Himalaya $HIM_VER"
else
    echo -e "${YELLOW}⚠${NC} Not found. Installing..."
    echo "  Download from: https://github.com/soywod/himalaya/releases"
    echo "  Or: curl -sSL https://github.com/soywod/himalaya/releases/latest/download/himalaya-linux-x86_64 -o ~/.local/bin/himalaya && chmod +x ~/.local/bin/himalaya"
    echo ""
fi

# ── Database ──
DB_PATH="$BASEDIR/sacco.db"
echo -n "Checking database... "
if [ -f "$DB_PATH" ]; then
    SIZE=$(ls -lh "$DB_PATH" | awk '{print $5}')
    echo -e "${GREEN}✓${NC} Found ($SIZE)"
else
    echo -e "${YELLOW}⚠${NC} Not found — will be created on first run"
fi

# ── Create sacco command ──
echo -n "Installing 'sacco' command... "
mkdir -p ~/.local/bin

cat > ~/.local/bin/sacco << ENDSCRIPT
#!/bin/bash
BASEDIR="$BASEDIR"
cd "\$BASEDIR"

if curl -s -o /dev/null http://127.0.0.1:9150/ 2>/dev/null; then
    echo "SACCO is already running!"
    echo "Dashboard: http://127.0.0.1:9150/dashboard"
    exit 0
fi

echo "Starting SACCO..."
python3 api_server.py &
PID=$!
sleep 3

if curl -s -o /dev/null http://127.0.0.1:9150/ 2>/dev/null; then
    echo "SACCO is running! PID: $PID"
    echo "Dashboard: http://127.0.0.1:9150/dashboard"
    echo "Stop: sacco-stop"
else
    echo "Failed to start."
fi
ENDSCRIPT

cat > ~/.local/bin/sacco-stop << 'ENDSTOP'
#!/bin/bash
pkill -f 'api_server.py' 2>/dev/null
echo "SACCO stopped."
ENDSTOP

chmod +x ~/.local/bin/sacco ~/.local/bin/sacco-stop
echo -e "${GREEN}✓${NC}"

# ── Ensure PATH ──
if ! echo "$PATH" | grep -q "$HOME/.local/bin"; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
    echo "  Added ~/.local/bin to PATH (restart terminal)"
fi

echo ""
echo "=============================="
echo -e "${GREEN}  Ready!${NC}"
echo "  Start:  sacco"
echo "  Stop:   sacco-stop"
echo "  URL:    http://127.0.0.1:9150/dashboard"
echo "=============================="
