#!/usr/bin/env bash

set -e

echo "===== Raspberry Pi + Thymio Setup ====="

#
# Update system
#

sudo apt update
sudo apt full-upgrade -y

#
# Basic tools
#

sudo apt install -y \
    git \
    python3-venv \
    python3-pip \
    flatpak \
    wget \
    curl

#
# Synchronize time
#

sudo date -s "$(wget -qSO- --max-redirect=0 google.com 2>&1 | grep Date: | cut -d' ' -f5-8)Z"

#
# Install Thymio Suite
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

#
# Add user to useful groups
#

sudo usermod -aG plugdev,dialout "$USER"

#
# Install Thymio Device Manager service
#

mkdir -p ~/.config/systemd/user

cat > ~/.config/systemd/user/thymio-device-manager.service <<EOF
[Unit]
Description=Thymio Device Manager

[Service]
ExecStart=/usr/bin/flatpak run --command=thymio-device-manager org.mobsya.ThymioSuite
Restart=always
RestartSec=2

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable thymio-device-manager.service

echo
echo "=========================================="
echo "Setup finished."
echo
echo "Reboot now:"
echo
echo "    sudo reboot"
echo
echo "After reboot plug in the Thymio."
echo "=========================================="