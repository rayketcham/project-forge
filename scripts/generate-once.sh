#!/bin/bash
# One-shot idea generation for cron
set -euo pipefail

cd /opt/project-forge
export FORGE_DB_PATH="${FORGE_DB_PATH:-/opt/project-forge/data/forge.db}"

exec python3 -m project_forge.cron.runner
