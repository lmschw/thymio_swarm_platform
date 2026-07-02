#!/usr/bin/env bash

set -euo pipefail

sudo date -s "$(wget -qSO- --max-redirect=0 google.com 2>&1 | grep Date: | cut -d' ' -f5-8)Z"

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
# Create environment config
#

sudo tee /etc/swarm-platform.conf >/dev/null <<EOF
SWARM_COORDINATOR=10.15.2.63
SWARM_COORDINATOR_PORT=9100
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
Environment=PATH=${PROJECT_DIR}/.venv/bin

ExecStart=${PROJECT_DIR}/.venv/bin/python -m swarm_platform.daemon.main

Restart=always
RestartSec=5

StandardOutput=append:${PROJECT_DIR}/swarm-daemon.log
StandardError=append:${PROJECT_DIR}/swarm-daemon.log

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
echo "Coordinator: 10.15.2.63:9100"
echo "Log file: ${PROJECT_DIR}/swarm-daemon.log"
echo "================================="