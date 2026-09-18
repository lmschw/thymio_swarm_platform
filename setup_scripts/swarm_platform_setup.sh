#!/usr/bin/env bash

set -euo pipefail

sudo date -s "$(wget -qSO- --max-redirect=0 google.com 2>&1 | grep Date: | cut -d' ' -f5-8)Z"

echo "===== Swarm Platform Setup ====="

PROJECT_DIR="$(pwd)"
CURRENT_USER="$USER"

# Coordinator address, centralised here so it only needs to be overridden in
# one place; matches the default in swarm_platform/config.py. Override by
# running e.g. `SWARM_COORDINATOR=192.168.1.10 ./setup_scripts/swarm_platform_setup.sh`.
SWARM_COORDINATOR="${SWARM_COORDINATOR:-10.15.2.63}"
SWARM_COORDINATOR_PORT="${SWARM_COORDINATOR_PORT:-9100}"

#
# Install uv if necessary
#
if ! command -v uv >/dev/null 2>&1; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh

    export PATH="$HOME/.local/bin:$PATH"
fi

UV_BIN="$(command -v uv)"

echo "Using uv: ${UV_BIN}"

#
# Install project dependencies
#
# The venv is created with access to system site-packages so that
# apt-installed hardware packages are importable from within it: picamera2
# (see setup_scripts/add_camera_support.sh) and, for the LED ring, lgpio --
# Blinka's board detection needs it on Pi 5 (bcm2712) even though the ring
# itself is driven over SPI, not GPIO bit-banging.
[ -d .venv ] || "${UV_BIN}" venv --system-site-packages
"${UV_BIN}" sync

#
# Install the Python SPI-Neopixel stack, for an optional WS2812B RGB LED
# ring (see swarm_platform/robot/led_ring.py). Plain pip packages, so safe
# to install unconditionally -- LedRing detects at runtime whether a ring
# is actually attached and never blocks robot startup if not.
#
"${UV_BIN}" pip install adafruit-blinka adafruit-circuitpython-neopixel-spi

#
# Create environment config
#
sudo tee /etc/swarm-platform.conf >/dev/null <<EOF
SWARM_COORDINATOR=${SWARM_COORDINATOR}
SWARM_COORDINATOR_PORT=${SWARM_COORDINATOR_PORT}
UV_BIN=${UV_BIN}
EOF

#
# Create swarm daemon service
#
sudo tee /etc/systemd/system/swarm-daemon.service >/dev/null <<EOF
[Unit]
Description=Swarm Platform Daemon
After=network.target

[Service]
Type=simple
User=${CURRENT_USER}
WorkingDirectory=${PROJECT_DIR}

EnvironmentFile=/etc/swarm-platform.conf
Environment=PYTHONUNBUFFERED=1

ExecStart=${UV_BIN} run -m swarm_platform.daemon.main

Restart=always
RestartSec=3

StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

#
# Reload systemd
#
sudo systemctl daemon-reload

#
# Enable and start daemon
#
sudo systemctl enable swarm-daemon.service
sudo systemctl restart swarm-daemon.service

echo
echo "================================="
echo "Swarm Platform installed"
echo "Daemon service enabled"
echo "Coordinator: ${SWARM_COORDINATOR}:${SWARM_COORDINATOR_PORT}"
echo "Project: ${PROJECT_DIR}"
echo "Using uv: ${UV_BIN}"
echo "================================="