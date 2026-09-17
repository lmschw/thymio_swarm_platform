#!/usr/bin/env bash

# Fresh Pis get LED ring support automatically from
# raspberry_pi_initial_setup.sh + swarm_platform_setup.sh -- you don't need
# to run this script for a new Pi. It's only for retrofitting a Pi that was
# set up before LED ring support existed (or where SPI/the spi group/the
# neopixel-spi packages got out of sync for some other reason).

set -euo pipefail

echo "===== Adding LED Ring Support ====="

#
# The ring's DIN wire goes to GPIO10/MOSI (physical pin 19), driven over
# hardware SPI -- not GPIO18/PWM. That's what lets the daemon talk to it as
# an unprivileged user (via /dev/spidev0.0, "spi" group permissions) instead
# of needing root, which the daemon (it clones and runs arbitrary project
# code) can't safely have.
#
echo "Enabling SPI interface..."
sudo raspi-config nonint do_spi 0

echo "Adding $USER to the spi group..."
sudo usermod -aG spi "$USER"

#
# Install the Python SPI-Neopixel stack into the project venv. Unlike
# picamera2, these are plain pip packages -- no apt/system-site-packages
# dance needed.
#
uv pip install adafruit-blinka adafruit-circuitpython-neopixel-spi

sudo systemctl restart swarm-daemon.service

echo
echo "================================="
echo "LED ring support installed"
echo "Daemon restarted"
echo
echo "NOTE: group membership changes only take effect in new login"
echo "sessions / services started after this point. If the daemon was"
echo "already running as $USER before this script added it to the spi"
echo "group, that restart above picks up the new group -- but your own"
echo "shell won't until you log out and back in."
echo "================================="
