#!/usr/bin/env bash
set -e

# Find Python executable
if command -v python3 &>/dev/null; then
    PYTHON=python3
elif command -v python &>/dev/null; then
    PYTHON=python
else
    echo "Error: Python not found. Please install Python 3." >&2
    exit 1
fi

echo "Python: $($PYTHON --version)"

echo "Creating virtual environment..."
$PYTHON -m venv .venv

echo "Installing requirements..."
.venv/bin/pip install --upgrade pip --quiet
.venv/bin/pip install -r requirements.txt

echo ""
echo "Setup complete. Activate with:"
echo "  source .venv/bin/activate"
