#!/usr/bin/env bash

set -e

if pgrep -f thymio-device-manager >/dev/null
then
    echo "TDM already running."
    exit 0
fi

echo "Starting Thymio Device Manager..."

nohup flatpak run \
    --command=thymio-device-manager \
    org.mobsya.ThymioSuite \
    >/tmp/thymio-device-manager.log 2>&1 &

sleep 5

echo "Done."