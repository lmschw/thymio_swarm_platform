#!/usr/bin/env bash

set -euo pipefail

echo "===== Raspberry Pi Swarm Setup ====="

sudo apt update
sudo apt full-upgrade -y

sudo apt install -y \
    git \
    python3-pip \
    python3-venv \
    flatpak \
    wget \
    curl
#
# Time
#

sudo date -s "$(wget -qSO- --max-redirect=0 google.com 2>&1 | grep Date: | cut -d' ' -f5-8)Z"

#
# Flatpak
#

sudo flatpak remote-add --if-not-exists flathub \
https://flathub.org/repo/flathub.flatpakrepo

sudo flatpak install -y flathub org.mobsya.ThymioSuite

#
# USB permissions
#

sudo tee /etc/udev/rules.d/99-thymio.rules >/dev/null <<EOF
SUBSYSTEM=="usb", ATTR{idVendor}=="0617", ATTR{idProduct}=="000a", MODE="0666"
SUBSYSTEM=="usb", ATTR{idVendor}=="0617", ATTR{idProduct}=="000c", MODE="0666"
EOF

sudo udevadm control --reload-rules
sudo udevadm trigger

sudo usermod -aG dialout,plugdev "$USER"

echo
echo "Reboot required."
echo