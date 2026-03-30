#!/bin/bash
# Initial setup for Project Forge
set -euo pipefail

cd /opt/project-forge

echo "=== Installing dependencies ==="
pip install --user --break-system-packages -e ".[dev,test]"

echo "=== Creating data directory ==="
mkdir -p data

echo "=== Running tests ==="
python3 -m pytest tests/ -v --tb=short

echo "=== Lint check ==="
python3 -m ruff check src/ tests/

echo "=== Setting up systemd service ==="
if [ -f /etc/systemd/system/project-forge-web.service ]; then
    echo "Service already exists, reloading..."
    sudo systemctl daemon-reload
    sudo systemctl restart project-forge-web
else
    echo "Installing systemd service..."
    sudo cp scripts/project-forge-web.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable project-forge-web
    sudo systemctl start project-forge-web
fi

echo "=== Setup complete ==="
echo "Dashboard: http://localhost:55443"
echo "Health: http://localhost:55443/health"
