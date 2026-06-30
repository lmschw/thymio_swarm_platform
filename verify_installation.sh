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

#
# TDM
#

echo "Checking TDM..."

python3 -m tdmclient list >/tmp/tdm_check.txt 2>/dev/null \
    || fail "Unable to communicate with the Thymio Device Manager."

pass "TDM responding"

echo

#
# Robot
#

echo "Checking connected Thymio..."

if grep -qi "node" /tmp/tdm_check.txt || grep -qi "Thymio" /tmp/tdm_check.txt; then
    pass "Thymio detected"
else
    warn "No Thymio detected (connect one if this is unexpected)"
fi

rm -f /tmp/tdm_check.txt

echo

#
# Python environment
#

echo "Checking virtual environment..."

test -d .venv \
    || fail ".venv not found. Run ./swarm_platform_setup.sh"

pass "Virtual environment exists"

echo

echo "Checking tdmclient..."

. .venv/bin/activate

python -c "import tdmclient" \
    || fail "tdmclient is not installed in the virtual environment."

pass "tdmclient installed"

deactivate

echo
echo "================================="
echo -e "${GREEN}Installation verified successfully.${NC}"
echo "================================="