#!/bin/bash
# Daily super idea synthesis - combines existing ideas into 5 mega-projects
set -euo pipefail

cd /opt/project-forge

if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

export FORGE_DB_PATH="${FORGE_DB_PATH:-/opt/project-forge/data/forge.db}"

echo "$(date): Generating daily super ideas..."
python3 -c "
import asyncio
from pathlib import Path
from project_forge.engine.super_ideas import SuperIdeaGenerator
from project_forge.storage.db import Database

async def main():
    db = Database(Path('$FORGE_DB_PATH'))
    await db.connect()
    gen = SuperIdeaGenerator(db)
    supers = await gen.generate(count=5)
    print(f'Generated {len(supers)} super ideas:')
    for si in supers:
        print(f'  [{si.impact_score:.2f}] {si.name} ({len(si.component_idea_ids)} components)')
    await db.close()

asyncio.run(main())
"
