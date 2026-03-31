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


def _content_hash(category: str, concept_idx: int, domain_idx: int, direction: str) -> str:
    """Deterministic content fingerprint from the generation inputs."""
    key = f"{category}:{concept_idx}:{domain_idx}:{direction}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def _make_name(concept: str, domain: str, direction: str, variant: int = 0) -> str:
    """Build idea name from concept + domain + variant for uniqueness."""
    words = concept.split()[:4]  # Use 4 words instead of 3 for more variety
    name_base = " ".join(w.capitalize() for w in words)
    domain_word = domain.split()[0].capitalize()
    if variant == 0:
        return f"{name_base} for {domain_word}" if len(name_base) < 35 else name_base
    # Variant suffixes for when the base name is taken
    suffixes = ["Pro", "Suite", "Hub", "Engine", "Platform", "Toolkit", "Lab", "Guard"]
    suffix = suffixes[variant % len(suffixes)]
    return f"{name_base} {suffix}" if len(name_base) < 35 else f"{name_base} {suffix}"


def generate_local_idea(
    category: IdeaCategory | None = None,
    recent_names: list[str] | None = None,
    used_tuples: set[str] | None = None,
) -> tuple[Idea, str, int, int, str]:
    """Generate an idea locally from seed data without API calls.

    Returns (idea, category_value, concept_idx, domain_idx, direction)
    so the caller can record the tuple.
    """
    recent = set(recent_names or [])
    used = used_tuples or set()

    if category is None:
        category = random.choice(list(IdeaCategory))

    seeds = CATEGORY_SEEDS[category]
    concepts = seeds["seed_concepts"]
    domains = seeds["domains_to_cross"]
    directions = ["basic", "contrarian", "combinatoric", "crossover"]

    # Try to find an unused tuple first
    concept_idx = random.randrange(len(concepts))
    domain_idx = random.randrange(len(domains))
    direction = random.choice(directions)

    # Search for unused tuple (up to 50 attempts)
    for _ in range(50):
        ch = _content_hash(category.value, concept_idx, domain_idx, direction)
        if ch not in used:
            break
        concept_idx = random.randrange(len(concepts))
        domain_idx = random.randrange(len(domains))
        direction = random.choice(directions)

    concept = concepts[concept_idx]
    domain = domains[domain_idx]
    ch = _content_hash(category.value, concept_idx, domain_idx, direction)

    # Build description based on direction
    if direction == "contrarian":
        prompt = random.choice(CONTRARIAN_PROMPTS)
        description = (
            f"Inspired by the question: {prompt}\n\n"
            f"{concept} applied to {domain}. "
            f"This project tackles an overlooked problem in {category.value} "
            "by approaching it from an unexpected angle."
        )
    elif direction == "combinatoric":
        template = random.choice(COMBINATORIC_TEMPLATES)
        other_cat = random.choice([c for c in IdeaCategory if c != category])
        other_concept = random.choice(CATEGORY_SEEDS[other_cat]["seed_concepts"])
        filled = template.format(
            concept_a=concept,
            concept_b=other_concept,
            domain_a=category.value,
            domain_b=other_cat.value,
        )
        description = (
            f"Cross-pollination: {filled}\n\n"
            f"Bridging {category.value} and {other_cat.value} "
            "to create something neither domain has alone."
        )
    elif direction == "crossover":
        other_cat = random.choice([c for c in IdeaCategory if c != category])
        other_domain = random.choice(CATEGORY_SEEDS[other_cat]["domains_to_cross"])
        description = (
            f"What happens when {concept} meets {other_domain}? "
            f"This project brings {category.value} thinking to {other_domain}, "
            "solving problems that domain experts haven't recognized yet."
        )
    else:
        description = (
            f"{concept} applied to {domain}. "
            f"This is a gap in the {category.value} space that nobody has filled. "
            "The intersection of these domains creates unique value."
        )

    # Generate unique name with variant fallback
    name = _make_name(concept, domain, direction)
    for variant in range(1, 10):
        if name not in recent:
            break
        name = _make_name(concept, domain, direction, variant)

    tagline = f"{concept[:80]} — tailored for {domain}"
    tech_stack = random.choice(TECH_STACKS.get(category, [["python", "fastapi"]]))
    score = round(random.uniform(0.55, 0.92), 2)

    idea = Idea(
        id=hashlib.sha256((name + str(datetime.now(UTC))).encode()).hexdigest()[:12],
        name=name,
        tagline=tagline[:120],
        description=description,
        category=category,
        market_analysis=(f"The {category.value} space lacks good tooling for {domain}. This fills a real gap."),
        feasibility_score=score,
        mvp_scope=(f"Build an MVP focused on {concept.split(',')[0].strip()} for {domain}. Target 2-4 week delivery."),
        tech_stack=tech_stack,
        content_hash=ch,
    )
    return idea, category.value, concept_idx, domain_idx, direction


async def run_auto_scan(db: Database, count: int = 5) -> list[Idea]:
    """Generate multiple ideas locally and store them.

    Uses input-tuple tracking to avoid regenerating the same
    (category, concept, domain, direction) combination.
    """
    # Load existing names (lightweight, names only)
    recent_names = set(await db.get_all_idea_names())

    # Load used tuples from DB
    cursor = await db.db.execute("SELECT category, concept_idx, domain_idx, direction FROM used_tuples")
    rows = await cursor.fetchall()
    used_tuples = {_content_hash(r[0], r[1], r[2], r[3]) for r in rows}

    ideas = []
    categories = list(IdeaCategory)
    random.shuffle(categories)

    for i in range(count):
        cat = categories[i % len(categories)]
        run = GenerationRun(category=cat)
        try:
            idea, cat_val, c_idx, d_idx, direction = generate_local_idea(
                category=cat,
                recent_names=list(recent_names),
                used_tuples=used_tuples,
            )
            await db.save_idea(idea)
            await db.record_used_tuple(cat_val, c_idx, d_idx, direction)
            used_tuples.add(_content_hash(cat_val, c_idx, d_idx, direction))
            recent_names.add(idea.name)
            ideas.append(idea)
            run.idea_id = idea.id
            run.success = True
            run.completed_at = datetime.now(UTC)
            await db.save_run(run)
            logger.info(
                "Auto-generated: %s (%s, %.2f)",
                idea.name,
                idea.category.value,
                idea.feasibility_score,
            )
        except Exception as e:
            run.error = str(e)
            run.completed_at = datetime.now(UTC)
            await db.save_run(run)
            logger.error("Auto-generation failed: %s", e)

    return ideas
