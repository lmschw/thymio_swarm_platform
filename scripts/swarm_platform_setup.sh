#!/usr/bin/env bash

set -euo pipefail

echo "===== Swarm Platform Setup ====="

#
# Create virtual environment
#

python3 -m venv .venv

source .venv/bin/activate

pip install --upgrade pip

#
# Install package
#

pip install -e .


# 
# Create configuration file
#

sudo tee /etc/swarm-platform.conf >/dev/null <<EOF
# Swarm Platform configuration

SWARM_COORDINATOR=10.15.2.96
SWARM_COORDINATOR_PORT=9100

# Reserved for future use
SWARM_ROBOT_PORT=9000
EOF

#
# Create swarm daemon service
#

PROJECT_DIR="$(pwd)"
CURRENT_USER="$USER"

sudo tee /etc/systemd/system/swarm-daemon.service >/dev/null <<EOF
[Unit]
Description=Swarm Platform Robot Daemon
After=network-online.target thymio-device-manager.service
Wants=network-online.target
Requires=thymio-device-manager.service

[Service]
Type=simple
User=${CURRENT_USER}
WorkingDirectory=${PROJECT_DIR}
Environment=PATH=${PROJECT_DIR}/.venv/bin
ExecStart=${PROJECT_DIR}/.venv/bin/python -m swarm_platform.daemon.main
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload

sudo systemctl enable swarm-daemon.service

sudo systemctl restart thymio-device-manager.service

sudo systemctl start swarm-daemon.service

echo
echo "================================="
echo "Swarm Platform installed."
echo "Run ./verify_installation.sh"
echo "================================="