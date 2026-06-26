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

flatpak --version >/dev/null || fail "Flatpak missing"

pass "Flatpak installed"

echo

echo "Checking Thymio Suite..."

flatpak info org.mobsya.ThymioSuite >/dev/null \
    || fail "Thymio Suite missing"

pass "Thymio Suite installed"

echo

echo "Checking USB rules..."

ls /etc/udev/rules.d/99-thymio.rules >/dev/null \
    || fail "udev rules missing"

pass "USB rules installed"


echo
echo "================================="
echo "Everything looks good!"
echo "================================="