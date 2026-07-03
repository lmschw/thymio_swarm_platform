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
    curl \
    uv

#
# Install uv (if not present)
#
if ! command -v uv &> /dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
fi

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

#
# Thymio Device Manager launcher
#

sudo tee /usr/local/bin/start-thymio-device-manager.sh >/dev/null <<'EOF'
#!/usr/bin/env bash

export DISPLAY=:0
export XDG_RUNTIME_DIR=/run/user/$(id -u)

exec /usr/bin/flatpak run \
    --command=thymio-device-manager \
    org.mobsya.ThymioSuite
EOF

sudo chmod +x /usr/local/bin/start-thymio-device-manager.sh

#
# systemd service
#

USER_NAME="$USER"
USER_ID="$(id -u)"

sudo tee /etc/systemd/system/thymio-device-manager.service >/dev/null <<EOF
[Unit]
Description=Thymio Device Manager
After=graphical.target network-online.target
Wants=graphical.target

[Service]
Type=simple
User=${USER_NAME}
Environment=DISPLAY=:0
Environment=XDG_RUNTIME_DIR=/run/user/${USER_ID}

ExecStart=/usr/local/bin/start-thymio-device-manager.sh

Restart=always
RestartSec=5

[Install]
WantedBy=graphical.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable thymio-device-manager.service

echo
echo "========================================="
echo "Setup complete."
echo
echo "Please reboot the Raspberry Pi:"
echo "    sudo reboot"
echo
echo "After reboot you can verify that the"
echo "Thymio Device Manager is running with:"
echo
echo "    systemctl status thymio-device-manager.service"
echo
echo "and"
echo
echo "    python3 -m tdmclient list"
echo "========================================="