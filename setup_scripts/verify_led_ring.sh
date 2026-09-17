#!/usr/bin/env bash

# Verifies that a Pi's LED ring is correctly installed, detected, importable
# from the project's virtual environment, and usable end-to-end through the
# platform's own LedRing class -- then, if the swarm daemon is running,
# confirms the live daemon process actually sees it too.
#
# Run this on the Pi itself, after the normal setup scripts
# (raspberry_pi_initial_setup.sh + swarm_platform_setup.sh), or after
# ./setup_scripts/add_led_ring_support.sh on an already-set-up Pi. The ring
# will flash red, green, then blue for a moment during the test.

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

echo "Checking SPI is enabled..."

if [ -e /boot/firmware/config.txt ]; then
    CONFIG_TXT=/boot/firmware/config.txt
else
    CONFIG_TXT=/boot/config.txt
fi

grep -q "^dtparam=spi=on" "$CONFIG_TXT" \
    || fail "SPI not enabled in $CONFIG_TXT (run ./setup_scripts/add_led_ring_support.sh, then reboot)"

pass "SPI enabled in $CONFIG_TXT"

echo

echo "Checking /dev/spidev0.0 exists and is accessible..."

test -e /dev/spidev0.0 \
    || fail "/dev/spidev0.0 missing -- reboot after enabling SPI?"

pass "/dev/spidev0.0 present"

groups "$USER" | grep -qw spi \
    || fail "$USER is not in the spi group (run ./setup_scripts/add_led_ring_support.sh, then log out and back in)"

pass "$USER is in the spi group"

echo

echo "Checking the project venv can import neopixel_spi..."

test -d .venv \
    || fail "Virtual environment missing"

.venv/bin/python -c "import board, neopixel_spi" \
    || fail "venv cannot import board/neopixel_spi (re-run ./setup_scripts/add_led_ring_support.sh)"

pass "board/neopixel_spi importable from .venv"

echo

echo "Driving the ring via swarm_platform.robot.led_ring.LedRing..."

.venv/bin/python - <<'EOF'
import asyncio
from swarm_platform.robot.led_ring import LedRing

async def main():
    ring = LedRing()
    await ring.start()
    assert ring.available, "LedRing.start() did not mark the ring as available"

    for color in [(32, 0, 0), (0, 32, 0), (0, 0, 32)]:
        await ring.fill(*color)
        await asyncio.sleep(0.5)

    await ring.stop()
    print(f"drove {ring.num_pixels} pixels")

asyncio.run(main())
EOF

pass "Ring driven and turned off"

echo

echo "Checking the running swarm-daemon (if any) reports the LED ring..."

if systemctl is-active swarm-daemon.service >/dev/null 2>&1; then

    STATUS_RESPONSE="$(python3 - <<'EOF'
import json
import socket

s = socket.create_connection(("127.0.0.1", 9000), timeout=5)
s.sendall((json.dumps({"type": "status"}) + "\n").encode())
print(s.recv(4096).decode().strip())
s.close()
EOF
)"

    echo "$STATUS_RESPONSE" | grep -q '"led_ring": *true' \
        || fail "Running swarm-daemon does not report led_ring: true. Response was: $STATUS_RESPONSE
    (Try: sudo systemctl restart swarm-daemon.service -- the ring is only detected once, at Robot.connect() time.)"

    pass "Running swarm-daemon reports led_ring: true"

else
    echo "swarm-daemon.service is not running -- skipping live daemon check."
    echo "(Start it with: sudo systemctl start swarm-daemon.service, then re-run this script.)"
fi

echo
echo "================================="
echo "LED ring verified"
echo "================================="
