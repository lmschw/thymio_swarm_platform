#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="swarm-coordinator"
USER_NAME="$(whoami)"
WORKDIR="$(pwd)"

cat <<EOF | sudo tee /etc/systemd/system/${SERVICE_NAME}.service >/dev/null
[Unit]
Description=Swarm Coordinator
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${USER_NAME}
WorkingDirectory=${WORKDIR}
ExecStart=/usr/bin/env uv run ${WORKDIR}/swarm_platform/coordinator/server.py

Restart=always
RestartSec=2

StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

echo "Reloading systemd..."
sudo systemctl daemon-reload

echo "Enabling ${SERVICE_NAME}..."
sudo systemctl enable ${SERVICE_NAME}

echo "Starting ${SERVICE_NAME}..."
sudo systemctl restart ${SERVICE_NAME}

echo
echo "=========================================="
echo "Swarm Coordinator installed successfully."
echo

systemctl --no-pager --full status ${SERVICE_NAME} || true

echo
echo "Listening sockets:"
ss -ltn | grep 9100 || echo "WARNING: Nothing is listening on port 9100."

echo
echo "Useful commands:"
echo "  systemctl status ${SERVICE_NAME}"
echo "  sudo systemctl restart ${SERVICE_NAME}"
echo "  sudo systemctl stop ${SERVICE_NAME}"
echo "  sudo systemctl disable ${SERVICE_NAME}"
echo "  journalctl -u ${SERVICE_NAME} -f"