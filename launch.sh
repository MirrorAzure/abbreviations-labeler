#!/usr/bin/env bash

# Check if virtualenv is installed
if ! python3 -m pip show virtualenv >/dev/null 2>&1; then
    echo "Package 'virtualenv' not installed."
    echo "Installing now..."
    python3 -m pip install virtualenv
else
    echo "Package 'virtualenv' installed."
fi

# Check if .venv exists
if [ ! -d ".venv" ]; then
    echo "Virtual environment .venv not found."
    echo "Creating virtual environment..."
    python3 -m venv .venv
else
    echo "Virtual environment .venv found."
fi

echo "Activating .venv..."
source .venv/bin/activate

echo "Installing packages from requirements.txt..."
python3 -m pip install -r requirements.txt

echo "Launching application..."
python3 src/abbreviation_labeler.py

deactivate