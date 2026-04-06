"""Tests for Team Review findings — security, operational, and quality fixes.

TDD RED phase: these tests define the expected behavior for fixes
identified by the Architect, SecOps, DevOps, and Tester review agents.

Issue tracking:
- #31: Constant-time token comparison (SecOps)
- #32: Health endpoint DB check (DevOps)
- #33: Independent multi-signal scorer (Architect)
- #34: Sanitize error detail in 502 responses (SecOps)
"""

import hmac

import pytest
from httpx import ASGITransport, AsyncClient

from project_forge.models import Idea, IdeaCategory


def _make_idea(name: str, **kw) -> Idea:
    return Idea(
        name=name,
        tagline=kw.get("tagline", f"{name} tagline"),
        description=kw.get("description", f"Description of {name}"),
        category=kw.get("category", IdeaCategory.SECURITY_TOOL),
        market_analysis="Good market.",
        feasibility_score=kw.get("score", 0.7),
        mvp_scope=kw.get("mvp_scope", "Build it."),
        tech_stack=kw.get("tech_stack", ["python"]),
    )


# ============================================================
# 1. CONSTANT-TIME TOKEN COMPARISON (SecOps #8)
# ============================================================


class TestConstantTimeTokenComparison:
    """Auth middleware must use hmac.compare_digest, not == for token comparison."""

    def test_auth_uses_hmac_compare_digest(self):
        """The auth module must use hmac.compare_digest for token comparison."""
        import inspect

        from project_forge.web.auth import BearerTokenMiddleware

        source = inspect.getsource(BearerTokenMiddleware)
        assert "compare_digest" in source, (
            "BearerTokenMiddleware must use hmac.compare_digest() for constant-time "
            "token comparison, not == which is vulnerable to timing attacks"
        )

    def test_hmac_compare_digest_correct(self):
        """Verify hmac.compare_digest works as expected for our use case."""
        tok = "test-value-123"  # noqa: S105
        assert hmac.compare_digest(f"Bearer {tok}", f"Bearer {tok}")
        assert not hmac.compare_digest(f"Bearer {tok}", "Bearer wrong")
        assert not hmac.compare_digest(f"Bearer {tok}", "")

    @pytest.mark.asyncio
    async def test_auth_rejects_wrong_token(self, tmp_path):
        """Auth middleware still rejects invalid tokens after the fix."""
        from project_forge.config import settings
        from project_forge.web.app import app, db

        original = settings.api_token
        settings.api_token = "test-secret-token"  # noqa: S105
        try:
            db.db_path = tmp_path / "test_auth_reject.db"
            await db.connect()
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/rounds",
                    json={"idea_ids": ["a", "b"]},
                    headers={"Authorization": "Bearer wrong-token"},
                )
                assert resp.status_code == 401
            await db.close()
        finally:
            settings.api_token = original

    @pytest.mark.asyncio
    async def test_auth_accepts_correct_token(self, tmp_path):
        """Auth middleware accepts valid tokens after the fix."""
        from project_forge.config import settings
        from project_forge.web.app import app, db

        original = settings.api_token
        settings.api_token = "test-secret-token"  # noqa: S105
        try:
            db.db_path = tmp_path / "test_auth_accept.db"
            await db.connect()
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                # Should not get 401 (may get 422 for bad data, but not 401)
                resp = await client.post(
                    "/api/rounds",
                    json={"idea_ids": ["a", "b"]},
                    headers={"Authorization": "Bearer test-secret-token"},
                )
                assert resp.status_code != 401
            await db.close()
        finally:
            settings.api_token = original


# ============================================================
# 2. HEALTH ENDPOINT WITH DB CHECK (DevOps)
# ============================================================


class TestHealthEndpointDBCheck:
    """Health endpoint must verify DB connectivity, not just return static 200."""

    @pytest.mark.asyncio
    async def test_health_includes_db_status(self, tmp_path):
        """Health response should include a db_ok field."""
        from project_forge.web.app import app, db

        db.db_path = tmp_path / "test_health_db.db"
        await db.connect()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")
            data = resp.json()
            assert "db_ok" in data, "Health endpoint must include db_ok field"
            assert data["db_ok"] is True
        await db.close()

    @pytest.mark.asyncio
    async def test_health_reports_db_failure(self, tmp_path):
        """Health endpoint should report db_ok=False when DB is unreachable."""
        from project_forge.web.app import app, db

        db.db_path = tmp_path / "test_health_fail.db"
        await db.connect()
        # Sabotage the connection by closing the underlying sqlite handle
        await db._db.close()
        db._db = None
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")
            data = resp.json()
            assert data["db_ok"] is False
        # Restore by reconnecting
        await db.connect()


# ============================================================
# 3. INDEPENDENT MULTI-SIGNAL SCORER (Architect)
# ============================================================


class TestIndependentScorer:
    """scorer.py must provide independent multi-signal scoring beyond LLM self-assessment."""

    def test_score_idea_function_exists(self):
        """scorer.py must have a score_idea() function that computes independent scores."""
        from project_forge.engine.scorer import score_idea

        idea = _make_idea(
            "PKI Cert Rotator",
            description="Automated X.509 certificate rotation for PKI infrastructure using ACME protocol. "
            "Monitors certificate expiry dates, triggers renewal via ACME, and deploys new certs.",
            mvp_scope="Build CLI that monitors cert expiry, triggers ACME renewal, deploys to target servers.",
            tech_stack=["Rust", "OpenSSL", "ACME"],
        )
        result = score_idea(idea)
        assert isinstance(result, dict)
        assert "specificity" in result
        assert "novelty" in result
        assert "composite" in result

    def test_specificity_score_rewards_concrete_details(self):
        """Ideas with specific tech references should score higher on specificity."""
        from project_forge.engine.scorer import score_idea

        specific = _make_idea(
            "ACME Cert Rotator",
            description="Automated X.509 certificate rotation using ACME protocol with RFC 8555 compliance. "
            "Integrates with HashiCorp Vault for secret storage. CLI built in Rust with OpenSSL bindings.",
            mvp_scope="Build a CLI tool that watches cert expiry via cron, calls ACME endpoints, deploys via SSH.",
            tech_stack=["Rust", "OpenSSL", "ACME", "Vault"],
        )
        vague = _make_idea(
            "Security Tool",
            description="A next-generation security tool that leverages AI to disrupt the compliance space.",
            mvp_scope="Build the thing.",
            tech_stack=["python"],
        )
        specific_result = score_idea(specific)
        vague_result = score_idea(vague)
        assert specific_result["specificity"] > vague_result["specificity"]

    def test_novelty_score_against_corpus(self):
        """Novelty should measure distance from existing ideas in a corpus."""
        from project_forge.engine.scorer import score_idea

        idea = _make_idea(
            "Unique Concept",
            description="A completely novel approach to quantum-resistant key exchange using lattice-based crypto.",
            tech_stack=["Rust", "liboqs"],
        )
        # With no corpus, novelty should be high (nothing to overlap with)
        result = score_idea(idea, corpus=[])
        assert result["novelty"] >= 0.8

        # With similar corpus ideas, novelty should drop
        similar = _make_idea(
            "Lattice Key Exchange",
            description="Quantum-resistant key exchange using lattice-based cryptography and post-quantum algorithms.",
            tech_stack=["Rust", "liboqs"],
        )
        result_with_corpus = score_idea(idea, corpus=[similar])
        assert result_with_corpus["novelty"] < result["novelty"]

    def test_composite_score_is_weighted_average(self):
        """Composite score should combine all signals into a 0-1 range."""
        from project_forge.engine.scorer import score_idea

        idea = _make_idea(
            "Test Composite",
            description="Automated certificate transparency log monitor with real-time alerting via webhook.",
            mvp_scope="Build a daemon that polls CT logs, parses entries, sends alerts via Slack webhook.",
            tech_stack=["Go", "CT-logs", "Slack"],
        )
        result = score_idea(idea)
        assert 0.0 <= result["composite"] <= 1.0

    def test_scope_realism_penalizes_overambition(self):
        """Ideas with unrealistically broad scope should get lower scores."""
        from project_forge.engine.scorer import score_idea

        realistic = _make_idea(
            "Simple Cert Monitor",
            description="CLI tool that checks X.509 certificate expiry dates and sends email alerts.",
            mvp_scope="Single binary, reads cert paths from config file, sends SMTP alerts.",
            tech_stack=["Go"],
        )
        overambitious = _make_idea(
            "Everything Platform",
            description="Full enterprise PKI platform with certificate authority, OCSP responder, "
            "CRL distribution, HSM integration, multi-tenant SaaS, Kubernetes operator, "
            "machine learning anomaly detection, and blockchain audit trail.",
            mvp_scope="Build all of the above plus mobile app, desktop client, browser extension, "
            "and API gateway with GraphQL and REST support in phases 1 through 4.",
            tech_stack=["Rust", "Go", "Python", "TypeScript", "Kubernetes", "ML", "blockchain"],
        )
        realistic_result = score_idea(realistic)
        overambitious_result = score_idea(overambitious)
        assert realistic_result["scope_realism"] > overambitious_result["scope_realism"]


# ============================================================
# 4. SANITIZE ERROR DETAIL IN 502 RESPONSES (SecOps #5)
# ============================================================


class TestErrorDetailSanitization:
    """502 error responses must not leak internal exception details."""

    def test_no_raw_exception_in_502_detail(self):
        """Verify that routes.py does not pass raw exception messages in 502 detail."""
        import inspect

        from project_forge.web import routes

        source = inspect.getsource(routes)
        # Find all HTTPException(status_code=502, ...) patterns
        # Should NOT contain f"...{exc}" or f"...{e}" in detail
        import re

        bad_patterns = re.findall(
            r'HTTPException\(status_code=502,\s*detail=f"[^"]*\{(?:exc|e)\}[^"]*"',
            source,
        )
        assert len(bad_patterns) == 0, (
            f"Found {len(bad_patterns)} HTTPException(502) responses that leak raw exception details: "
            f"{bad_patterns}. Use generic messages and log the exception server-side."
        )
