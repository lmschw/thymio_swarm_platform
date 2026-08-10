#!/usr/bin/env bash

# Verifies that a Pi's camera is correctly installed, detected, importable
# from the project's virtual environment, and usable end-to-end through the
# platform's own Camera class -- then, if the swarm daemon is running,
# confirms the live daemon process actually sees it too.
#
# Run this on the Pi itself, after ./setup_scripts/add_camera_support.sh
# (or after raspberry_pi_initial_setup.sh + swarm_platform_setup.sh on a
# fresh Pi). A JPEG test capture is left at /tmp/camera_test_capture.jpg for
# manual visual inspection (e.g. scp it back to your laptop and open it).

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

echo "Checking python3-picamera2 apt package..."

dpkg -s python3-picamera2 >/dev/null 2>&1 \
    || fail "python3-picamera2 not installed (run ./setup_scripts/add_camera_support.sh)"

pass "python3-picamera2 installed"

echo

echo "Checking camera is detected at the OS/libcamera level..."

if command -v rpicam-hello >/dev/null 2>&1; then
    LIST_CMD="rpicam-hello --list-cameras"
elif command -v libcamera-hello >/dev/null 2>&1; then
    LIST_CMD="libcamera-hello --list-cameras"
else
    fail "Neither rpicam-hello nor libcamera-hello found -- is the libcamera stack installed?"
fi

CAMERA_LIST="$($LIST_CMD 2>&1)"

echo "$CAMERA_LIST" | grep -qi "Available cameras" \
    && ! echo "$CAMERA_LIST" | grep -qi "no cameras available" \
    || fail "No camera detected by libcamera. Check the CSI cable is seated correctly (blue side towards the USB ports on most Pi models) and reboot after connecting it.
    Output was:
$CAMERA_LIST"

pass "Camera detected by libcamera"

echo

echo "Checking the project venv can import picamera2..."

test -d .venv \
    || fail "Virtual environment missing"

.venv/bin/python -c "import picamera2" \
    || fail "venv cannot import picamera2 -- was it created with --system-site-packages? (re-run ./setup_scripts/add_camera_support.sh)"

pass "picamera2 importable from .venv"

echo

echo "Capturing a test image via swarm_platform.robot.camera.Camera..."

rm -f /tmp/camera_test_capture.jpg

.venv/bin/python - <<'EOF'
import asyncio
from swarm_platform.robot.camera import Camera

async def main():
    cam = Camera()
    await cam.start()
    assert cam.available, "Camera.start() did not mark the camera as available"

    data = await cam.capture("/tmp/camera_test_capture.jpg")
    assert len(data) > 0, "captured 0 bytes"

    await cam.stop()
    print(f"captured {len(data)} bytes")

asyncio.run(main())
EOF

test -s /tmp/camera_test_capture.jpg \
    || fail "Test capture file missing or empty"

pass "Test image captured to /tmp/camera_test_capture.jpg ($(stat -c%s /tmp/camera_test_capture.jpg) bytes)"

echo

echo "Checking the running swarm-daemon (if any) reports the camera..."

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

    echo "$STATUS_RESPONSE" | grep -q '"camera": *true' \
        || fail "Running swarm-daemon does not report camera: true. Response was: $STATUS_RESPONSE
    (Try: sudo systemctl restart swarm-daemon.service -- the camera is only detected once, at Robot.connect() time.)"

    pass "Running swarm-daemon reports camera: true"

else
    echo "swarm-daemon.service is not running -- skipping live daemon check."
    echo "(Start it with: sudo systemctl start swarm-daemon.service, then re-run this script.)"
fi

echo
echo "================================="
echo "Camera verified"
echo "Inspect /tmp/camera_test_capture.jpg manually (e.g. scp it to your laptop) to confirm the image itself looks correct."
echo "================================="
