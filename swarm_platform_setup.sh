#!/usr/bin/env bash

set -e

python3 -m venv .venv

source .venv/bin/activate

python -m pip install --upgrade pip

pip install -e .

echo
echo "Swarm platform installed."
echo
echo "Activate with:"
echo
echo "source .venv/bin/activate"