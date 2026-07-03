#!/usr/bin/env bash

set -euo pipefail

sudo date -s "$(wget -qSO- --max-redirect=0 google.com 2>&1 | grep Date: | cut -d' ' -f5-8)Z"

echo "===== Swarm Platform Setup ====="

PROJECT_DIR="$(pwd)"
CURRENT_USER="$USER"

#
# Install dependencies (deterministic)
#
uv sync

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
User=thymio
WorkingDirectory=/home/thymio/swarm/thymio_swarm_platform

EnvironmentFile=/etc/swarm-platform.conf
Environment=PYTHONUNBUFFERED=1

ExecStart=/home/thymio/.local/bin/uv run swarm_platform.daemon.main

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
echo "Coordinator: 10.15.2.63:9100"
echo "================================="