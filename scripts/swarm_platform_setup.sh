#!/usr/bin/env bash

set -euo pipefail

echo "===== Swarm Platform Setup ====="

PROJECT_DIR="$(pwd)"
CURRENT_USER="$USER"

#
# Create virtual environment
#

python3 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install -e .

#
# Create environment config (IMPORTANT)
#

sudo tee /etc/swarm-platform.conf >/dev/null <<EOF
# Swarm Platform configuration
SWARM_COORDINATOR=10.15.2.96
SWARM_COORDINATOR_PORT=9100
EOF

#
# Create swarm daemon service
#

sudo tee /etc/systemd/system/swarm-daemon.service >/dev/null <<EOF
[Unit]
Description=Swarm Platform Robot Daemon
After=network-online.target thymio-device-manager.service
Wants=network-online.target
Requires=thymio-device-manager.service

[Service]
Type=simple
User=thymio
WorkingDirectory=/home/thymio/swarm/thymio_swarm_platform

Environment=SWARM_COORDINATOR=10.15.2.96
Environment=SWARM_COORDINATOR_PORT=9100

Environment=PATH=/home/thymio/swarm/thymio_swarm_platform/.venv/bin

ExecStart=/home/thymio/swarm/thymio_swarm_platform/.venv/bin/python -m swarm_platform.daemon.main

Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

#
# Reload systemd and enable service
#

sudo systemctl daemon-reload
sudo systemctl enable swarm-daemon.service
sudo systemctl restart swarm-daemon.service

echo
echo "================================="
echo "Swarm Platform installed"
echo "Daemon service enabled"
echo "Config: /etc/swarm-platform.conf"
echo "================================="