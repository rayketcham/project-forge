"""Tests for category definitions."""

from project_forge.engine.categories import (
    CATEGORY_SEEDS,
    COMBINATORIC_TEMPLATES,
    CONTRARIAN_PROMPTS,
)
from project_forge.models import IdeaCategory


def test_all_categories_have_seeds():
    for category in IdeaCategory:
        assert category in CATEGORY_SEEDS, f"Missing seeds for {category}"
        seeds = CATEGORY_SEEDS[category]
        assert "description" in seeds
        assert "seed_concepts" in seeds
        assert "domains_to_cross" in seeds
        assert len(seeds["seed_concepts"]) >= 5
        assert len(seeds["domains_to_cross"]) >= 3


def test_combinatoric_templates_have_placeholders():
    for template in COMBINATORIC_TEMPLATES:
        assert "{" in template


def test_contrarian_prompts_are_questions():
    for prompt in CONTRARIAN_PROMPTS:
        assert prompt.endswith("?")


def test_category_seeds_no_duplicates():
    for category, seeds in CATEGORY_SEEDS.items():
        concepts = seeds["seed_concepts"]
        assert len(concepts) == len(set(concepts)), f"Duplicate seeds in {category}"
