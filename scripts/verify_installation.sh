#!/usr/bin/env bash

set -e

GREEN="\033[0;32m"
RED="\033[0;31m"
YELLOW="\033[1;33m"
NC="\033[0m"

pass() {
    echo -e "${GREEN}✓${NC} $1"
}

warn() {
    echo -e "${YELLOW}!${NC} $1"
}

fail() {
    echo -e "${RED}✗${NC} $1"
    exit 1
}

echo "===== Verifying Raspberry Pi Swarm Platform ====="
echo

#
# Flatpak
#

echo "Checking Flatpak..."

flatpak --version >/dev/null \
    || fail "Flatpak is not installed."

pass "Flatpak installed"

echo

#
# Thymio Suite
#

echo "Checking Thymio Suite..."

flatpak info org.mobsya.ThymioSuite >/dev/null \
    || fail "Thymio Suite is not installed."

pass "Thymio Suite installed"

echo

#
# udev rules
#

echo "Checking USB permissions..."

test -f /etc/udev/rules.d/99-thymio.rules \
    || fail "99-thymio.rules missing."

pass "USB rules installed"

echo

#
# systemd service
#

echo "Checking Thymio Device Manager service..."

systemctl list-unit-files | grep -q "^thymio-device-manager.service" \
    || fail "Service not installed."

pass "Service installed"

systemctl is-enabled thymio-device-manager.service >/dev/null \
    || fail "Service is not enabled."

pass "Service enabled"

systemctl is-active thymio-device-manager.service >/dev/null \
    || fail "Service is not running."

pass "Service running"

echo

echo "Checking Python connection..."

source .venv/bin/activate

python <<'EOF'
from tdmclient import ClientAsync

with ClientAsync() as client:
    for _ in range(50):
        client.process_waiting_messages()
        if list(client.nodes):
            print("OK")
            raise SystemExit(0)

import sys
sys.exit(1)
EOF

if [ $? -eq 0 ]; then
    pass "Python can discover a Thymio"
else
    warn "Python could not discover a Thymio"
fi

deactivate

echo
echo "================================="
echo -e "${GREEN}Installation verified successfully.${NC}"
echo "================================="