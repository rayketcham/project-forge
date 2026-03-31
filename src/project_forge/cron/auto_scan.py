"""Automated idea generation from seed data - no API key required.

Generates new project ideas by combining seed concepts, domains, and
contrarian prompts from the category database. Creates unique ideas
by cross-pollinating concepts across categories.
"""

import hashlib
import logging
import random
from datetime import UTC, datetime

from project_forge.engine.categories import CATEGORY_SEEDS, COMBINATORIC_TEMPLATES, CONTRARIAN_PROMPTS
from project_forge.models import GenerationRun, Idea, IdeaCategory
from project_forge.storage.db import Database

logger = logging.getLogger(__name__)

# Pre-built idea templates from deep research
IDEA_TEMPLATES = [
    {
        "pattern": "{concept} for {domain}",
        "name_pattern": "{concept_short} {domain_short} Tool",
    },
    {
        "pattern": "Automated {concept} with {approach}",
        "name_pattern": "Auto-{concept_short}",
    },
    {
        "pattern": "{concept_a} meets {concept_b}: bridging {domain_a} and {domain_b}",
        "name_pattern": "{concept_a_short}-{concept_b_short} Bridge",
    },
]

TECH_STACKS = {
    IdeaCategory.PQC_CRYPTOGRAPHY: [
        ["python", "cryptography", "oqs-provider"],
        ["rust", "openssl", "pkcs11"],
        ["go", "crypto", "grpc"],
    ],
    IdeaCategory.NIST_STANDARDS: [
        ["python", "fastapi", "boto3"],
        ["python", "click", "jinja2"],
        ["python", "pytest", "cryptography"],
    ],
    IdeaCategory.RFC_SECURITY: [
        ["python", "httpx", "fastapi"],
        ["python", "cryptography", "pyasn1"],
        ["go", "grpc", "protobuf"],
    ],
    IdeaCategory.CRYPTO_INFRASTRUCTURE: [
        ["python", "cryptography", "sqlite"],
        ["rust", "pkcs11", "tokio"],
        ["python", "fastapi", "redis"],
    ],
    IdeaCategory.SECURITY_TOOL: [["python", "click", "httpx"], ["rust", "tokio", "serde"], ["go", "cobra", "grpc"]],
    IdeaCategory.VULNERABILITY_RESEARCH: [
        ["python", "scapy", "httpx"],
        ["python", "click", "beautifulsoup4"],
        ["rust", "nom", "tokio"],
    ],
    IdeaCategory.COMPLIANCE: [
        ["python", "fastapi", "boto3"],
        ["python", "click", "jinja2"],
        ["python", "sqlalchemy", "httpx"],
    ],
    IdeaCategory.PRIVACY: [
        ["python", "spacy", "kafka-python"],
        ["go", "redis", "grpc"],
        ["python", "pandas", "scikit-learn"],
    ],
    IdeaCategory.AUTOMATION: [
        ["python", "fastapi", "anthropic"],
        ["python", "click", "gitpython"],
        ["python", "celery", "redis"],
    ],
    IdeaCategory.DEVOPS_TOOLING: [
        ["python", "fastapi", "d3.js"],
        ["go", "kubernetes", "prometheus"],
        ["python", "boto3", "terraform"],
    ],
    IdeaCategory.OBSERVABILITY: [
        ["python", "prometheus-client", "fastapi"],
        ["go", "opentelemetry", "grpc"],
        ["python", "elasticsearch", "click"],
    ],
    IdeaCategory.MARKET_GAP: [
        ["python", "fastapi", "httpx"],
        ["node", "express", "react"],
        ["python", "django", "celery"],
    ],
}


def _generate_idea_id(name: str) -> str:
    """Generate a deterministic short ID from the idea name."""
    return hashlib.sha256(name.encode()).hexdigest()[:12]


def generate_local_idea(
    category: IdeaCategory | None = None,
    recent_names: list[str] | None = None,
) -> Idea:
    """Generate an idea locally from seed data without API calls."""
    recent = set(recent_names or [])

    # Pick category
    if category is None:
        category = random.choice(list(IdeaCategory))

    seeds = CATEGORY_SEEDS[category]
    concept = random.choice(seeds["seed_concepts"])
    domain = random.choice(seeds["domains_to_cross"])

    # Pick a creative direction
    direction = random.choice(["basic", "contrarian", "combinatoric", "crossover"])

    if direction == "contrarian":
        prompt = random.choice(CONTRARIAN_PROMPTS)
        description = f"Inspired by the question: {prompt}\n\n{concept} applied to {domain}. "
        description += (
            f"This project tackles an overlooked problem in {category.value} "
            "by approaching it from an unexpected angle."
        )
    elif direction == "combinatoric":
        template = random.choice(COMBINATORIC_TEMPLATES)
        other_cat = random.choice([c for c in IdeaCategory if c != category])
        other_seeds = CATEGORY_SEEDS[other_cat]
        other_concept = random.choice(other_seeds["seed_concepts"])
        filled = template.format(
            concept_a=concept,
            concept_b=other_concept,
            domain_a=category.value,
            domain_b=other_cat.value,
        )
        description = f"Cross-pollination: {filled}\n\n"
        description += f"Bridging {category.value} and {other_cat.value} to create something neither domain has alone."
    elif direction == "crossover":
        other_cat = random.choice([c for c in IdeaCategory if c != category])
        other_domain = random.choice(CATEGORY_SEEDS[other_cat]["domains_to_cross"])
        description = f"What happens when {concept} meets {other_domain}? "
        description += f"This project brings {category.value} thinking to {other_domain}, "
        description += "solving problems that domain experts haven't recognized yet."
    else:
        description = f"{concept} applied to {domain}. "
        description += f"This is a gap in the {category.value} space that nobody has filled. "
        description += "The intersection of these domains creates unique value."

    # Generate name
    words = concept.split()[:3]
    name_base = " ".join(w.capitalize() for w in words)
    name = f"{name_base} for {domain.split()[0].capitalize()}" if len(name_base) < 30 else name_base

    # Avoid duplicates
    attempts = 0
    while name in recent and attempts < 10:
        concept = random.choice(seeds["seed_concepts"])
        words = concept.split()[:3]
        name_base = " ".join(w.capitalize() for w in words)
        name = f"{name_base} for {domain.split()[0].capitalize()}" if len(name_base) < 30 else name_base
        attempts += 1

    tagline = f"{concept[:80]} — tailored for {domain}"
    tech_stack = random.choice(TECH_STACKS.get(category, [["python", "fastapi"]]))
    score = round(random.uniform(0.55, 0.92), 2)

    return Idea(
        id=_generate_idea_id(name + str(datetime.now(UTC))),
        name=name,
        tagline=tagline[:120],
        description=description,
        category=category,
        market_analysis=f"The {category.value} space lacks good tooling for {domain}. This fills a real gap.",
        feasibility_score=score,
        mvp_scope=f"Build an MVP focused on {concept.split(',')[0].strip()} for {domain}. Target 2-4 week delivery.",
        tech_stack=tech_stack,
    )


async def run_auto_scan(db: Database, count: int = 5) -> list[Idea]:
    """Generate multiple ideas locally and store them."""
    existing = await db.list_ideas(limit=1000)
    recent_names = [i.name for i in existing]

    ideas = []
    categories = list(IdeaCategory)
    random.shuffle(categories)

    for i in range(count):
        cat = categories[i % len(categories)]
        run = GenerationRun(category=cat)
        try:
            idea = generate_local_idea(category=cat, recent_names=recent_names + [i.name for i in ideas])
            await db.save_idea(idea)
            ideas.append(idea)
            run.idea_id = idea.id
            run.success = True
            run.completed_at = datetime.now(UTC)
            await db.save_run(run)
            logger.info("Auto-generated: %s (%s, %.2f)", idea.name, idea.category.value, idea.feasibility_score)
        except Exception as e:
            run.error = str(e)
            run.completed_at = datetime.now(UTC)
            await db.save_run(run)
            logger.error("Auto-generation failed: %s", e)

    return ideas
