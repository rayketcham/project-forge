"""Tests for idea generator with mocked Anthropic API."""

import json
from unittest.mock import MagicMock, patch

import pytest

from project_forge.engine.generator import IdeaGenerator
from project_forge.models import IdeaCategory

MOCK_IDEA_DATA = {
    "name": "Ghost Keys",
    "tagline": "Detect orphaned API keys across your entire infrastructure",
    "description": (
        "Ghost Keys scans your infrastructure for API keys that are still active "
        "but no longer used by any service. It integrates with cloud providers, "
        "secret managers, and application logs to build a dependency graph of key usage."
    ),
    "category": "security-tool",
    "market_analysis": (
        "API key sprawl is a growing problem as organizations adopt more SaaS tools. "
        "Existing secret scanners find exposed keys but don't track usage."
    ),
    "feasibility_score": 0.82,
    "mvp_scope": (
        "CLI tool that scans AWS IAM, GitHub tokens, and common secret managers. "
        "Reports unused keys older than 30 days."
    ),
    "tech_stack": ["python", "boto3", "click", "sqlite"],
}

MOCK_RESPONSE_JSON = json.dumps(MOCK_IDEA_DATA)


def _make_mock_response(text: str) -> MagicMock:
    mock_content = MagicMock()
    mock_content.text = text
    mock_response = MagicMock()
    mock_response.content = [mock_content]
    return mock_response


class TestIdeaGenerator:
    @patch("project_forge.engine.generator.anthropic.Anthropic")
    @pytest.mark.asyncio
    async def test_generate_idea(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.return_value = _make_mock_response(MOCK_RESPONSE_JSON)

        gen = IdeaGenerator(api_key="test-key")
        idea = await gen.generate(category=IdeaCategory.SECURITY_TOOL)

        assert idea.name == "Ghost Keys"
        assert idea.category == IdeaCategory.SECURITY_TOOL
        assert idea.feasibility_score == 0.82
        assert "python" in idea.tech_stack
        assert idea.status == "new"

    @patch("project_forge.engine.generator.anthropic.Anthropic")
    @pytest.mark.asyncio
    async def test_generate_handles_markdown_code_block(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        wrapped = f"Here's the idea:\n```json\n{MOCK_RESPONSE_JSON}\n```\n"
        mock_client.messages.create.return_value = _make_mock_response(wrapped)

        gen = IdeaGenerator(api_key="test-key")
        idea = await gen.generate(category=IdeaCategory.SECURITY_TOOL)

        assert idea.name == "Ghost Keys"

    @patch("project_forge.engine.generator.anthropic.Anthropic")
    @pytest.mark.asyncio
    async def test_generate_clamps_score(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        data = dict(MOCK_IDEA_DATA)
        data["feasibility_score"] = 1.5
        mock_client.messages.create.return_value = _make_mock_response(json.dumps(data))

        gen = IdeaGenerator(api_key="test-key")
        idea = await gen.generate(category=IdeaCategory.SECURITY_TOOL)

        assert idea.feasibility_score == 1.0

    @patch("project_forge.engine.generator.anthropic.Anthropic")
    @pytest.mark.asyncio
    async def test_generate_with_recent_ideas(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.return_value = _make_mock_response(MOCK_RESPONSE_JSON)

        gen = IdeaGenerator(api_key="test-key")
        idea = await gen.generate(
            category=IdeaCategory.SECURITY_TOOL,
            recent_ideas=["Previous Idea 1", "Previous Idea 2"],
        )

        assert idea.name == "Ghost Keys"
        call_args = mock_client.messages.create.call_args
        user_msg = call_args.kwargs["messages"][0]["content"]
        assert "Previous Idea 1" in user_msg
