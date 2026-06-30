#!/usr/bin/env bash

set -euo pipefail

python3 -m venv .venv

source .venv/bin/activate

sudo date -s "$(wget -qSO- --max-redirect=0 google.com 2>&1 | grep Date: | cut -d' ' -f5-8)Z"

python -m pip install --upgrade pip

pip install -e .

echo
echo "Project installed."