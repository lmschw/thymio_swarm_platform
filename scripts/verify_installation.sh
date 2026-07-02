#!/usr/bin/env bash

set -e

GREEN="\033[0;32m"
RED="\033[0;31m"
NC="\033[0m"

pass() {
    echo -e "${GREEN}✓${NC} $1"
}

fail() {
    echo -e "${RED}✗${NC} $1"
    exit 1
}

echo "Checking Flatpak..."

flatpak --version >/dev/null \
    || fail "Flatpak missing"

pass "Flatpak installed"

echo

echo "Checking Thymio Suite..."

flatpak info org.mobsya.ThymioSuite >/dev/null \
    || fail "Thymio Suite missing"

pass "Thymio Suite installed"

echo

echo "Checking USB rules..."

test -f /etc/udev/rules.d/99-thymio.rules \
    || fail "USB rules missing"

pass "USB rules installed"

echo

echo "Checking Thymio Device Manager service..."

systemctl list-unit-files | grep -q "^thymio-device-manager.service" \
    || fail "TDM service not installed"

pass "TDM service installed"

systemctl is-enabled thymio-device-manager.service >/dev/null \
    || fail "TDM service not enabled"

pass "TDM service enabled"

systemctl is-active thymio-device-manager.service >/dev/null \
    || fail "TDM service not running"

pass "TDM service running"

ss -ltn | grep -q ":8596 " \
    || fail "TDM is not listening on port 8596"

pass "TDM listening on port 8596"

echo

echo "Checking Python environment..."

test -d .venv \
    || fail "Virtual environment missing"

pass "Virtual environment exists"

.venv/bin/python - <<EOF >/dev/null
import swarm_platform
from swarm_platform.daemon.server import SwarmDaemon
print("OK")
EOF

pass "Python package imports successfully"

echo

echo "Checking Swarm daemon service..."

systemctl list-unit-files | grep -q "^swarm-daemon.service" \
    || fail "Swarm daemon service not installed"

pass "Swarm daemon service installed"

systemctl is-enabled swarm-daemon.service >/dev/null \
    || fail "Swarm daemon service not enabled"

pass "Swarm daemon service enabled"

systemctl is-active swarm-daemon.service >/dev/null \
    || fail "Swarm daemon service not running"

pass "Swarm daemon service running"

echo
echo "================================="
echo "Everything looks good!"
echo "================================="