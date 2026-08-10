#!/usr/bin/env bash

set -euo pipefail

echo "===== Adding Pi Camera Support ====="

#
# Install picamera2 (and the libcamera stack it depends on) via apt --
# this is the reliable way to get it on Raspberry Pi OS.
#
sudo apt update
sudo apt install -y python3-picamera2

#
# Recreate the project venv with access to system site-packages so the
# apt-installed picamera2/libcamera bindings are importable from it, then
# reinstall the project's own dependencies into it.
#
sudo systemctl stop swarm-daemon.service

rm -rf .venv
uv venv --system-site-packages
uv sync

sudo systemctl start swarm-daemon.service

echo
echo "================================="
echo "Camera support installed"
echo "Daemon restarted"
echo "================================="
