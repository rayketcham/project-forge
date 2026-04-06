"""Tests for Selection Rounds, Idea-to-Idea Comparison, and Denial with Reasoning.

TDD RED phase: all tests should FAIL before implementation.
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from project_forge.models import Idea, IdeaCategory

# === Helper to create test ideas ===


def _make_idea(name: str, score: float = 0.7, category: IdeaCategory = IdeaCategory.SECURITY_TOOL, **kw) -> Idea:
    return Idea(
        name=name,
        tagline=kw.get("tagline", f"{name} tagline"),
        description=kw.get("description", f"Description of {name}"),
        category=category,
        market_analysis="Good market.",
        feasibility_score=score,
        mvp_scope="Build it.",
        tech_stack=kw.get("tech_stack", ["python"]),
    )


# ============================================================
# 1. DENIAL WITH REASONING — Model + DB
# ============================================================


class TestDenialModel:
    """IdeaDenial Pydantic model validation."""

    def test_denial_model_exists(self):
        from project_forge.models import IdeaDenial

        denial = IdeaDenial(
            idea_id="abc123",
            reason="Too similar to existing PKI tooling",
        )
        assert denial.idea_id == "abc123"
        assert denial.reason == "Too similar to existing PKI tooling"
        assert denial.id  # auto-generated
        assert denial.denied_at  # auto-generated

    def test_denial_requires_reason(self):
        from project_forge.models import IdeaDenial

        with pytest.raises(ValidationError):
            IdeaDenial(idea_id="abc123", reason="")

    def test_denial_has_optional_denied_by(self):
        from project_forge.models import IdeaDenial

        denial = IdeaDenial(
            idea_id="abc123",
            reason="Duplicate concept",
            denied_by="review_cycle",
        )
        assert denial.denied_by == "review_cycle"

    def test_denial_default_denied_by_is_none(self):
        from project_forge.models import IdeaDenial

        denial = IdeaDenial(idea_id="abc123", reason="Low feasibility")
        assert denial.denied_by is None


class TestDenialDB:
    """IdeaDenial persistence in SQLite."""

    @pytest.mark.asyncio
    async def test_save_denial(self, db):
        from project_forge.models import IdeaDenial

        idea = _make_idea("Denial Target")
        await db.save_idea(idea)

        denial = IdeaDenial(idea_id=idea.id, reason="Overlaps with pki-ca-engine")
        saved = await db.save_denial(denial)
        assert saved.id == denial.id

    @pytest.mark.asyncio
    async def test_get_denials_for_idea(self, db):
        from project_forge.models import IdeaDenial

        idea = _make_idea("Denied Idea")
        await db.save_idea(idea)

        d1 = IdeaDenial(idea_id=idea.id, reason="First denial: too broad")
        d2 = IdeaDenial(idea_id=idea.id, reason="Second denial: market saturated")
        await db.save_denial(d1)
        await db.save_denial(d2)

        denials = await db.get_denials(idea.id)
        assert len(denials) == 2
        reasons = [d.reason for d in denials]
        assert "First denial: too broad" in reasons
        assert "Second denial: market saturated" in reasons

    @pytest.mark.asyncio
    async def test_denial_updates_idea_status(self, db):
        """Saving a denial should also set the idea status to 'rejected'."""
        from project_forge.models import IdeaDenial

        idea = _make_idea("Auto-Reject Me")
        await db.save_idea(idea)
        assert (await db.get_idea(idea.id)).status == "new"

        denial = IdeaDenial(idea_id=idea.id, reason="Killed by review")
        await db.save_denial(denial)

        updated = await db.get_idea(idea.id)
        assert updated.status == "rejected"

    @pytest.mark.asyncio
    async def test_get_denials_empty(self, db):
        denials = await db.get_denials("nonexistent_id")
        assert denials == []

    @pytest.mark.asyncio
    async def test_denial_with_denied_by(self, db):
        from project_forge.models import IdeaDenial

        idea = _make_idea("Manual Denied")
        await db.save_idea(idea)

        denial = IdeaDenial(idea_id=idea.id, reason="Manual rejection", denied_by="user:ray")
        await db.save_denial(denial)

        denials = await db.get_denials(idea.id)
        assert denials[0].denied_by == "user:ray"


# ============================================================
# 2. IDEA-TO-IDEA COMPARISON
# ============================================================


class TestIdeaComparison:
    """compare_ideas: head-to-head idea comparison using keyword overlap."""

    def test_compare_ideas_exists(self):
        from project_forge.engine.compare import compare_ideas

        a = _make_idea(
            "PKI Cert Manager",
            tagline="Manage X.509 certificates",
            description="Certificate lifecycle management for PKI infrastructure",
            tech_stack=["Rust", "OpenSSL"],
        )
        b = _make_idea(
            "PKI Revocation Dashboard",
            tagline="CRL management for PKI",
            description="Dashboard for certificate revocation lists in PKI systems",
            tech_stack=["Python", "FastAPI"],
        )
        result = compare_ideas(a, b)
        assert "overlap_score" in result
        assert "verdict" in result
        assert "matching_keywords" in result
        assert "winner" in result

    def test_compare_similar_ideas_high_overlap(self):
        from project_forge.engine.compare import compare_ideas

        a = _make_idea(
            "PKI Cert Issuer",
            tagline="Issue X.509 certificates via ACME",
            description="Build a PKI certificate authority with ACME protocol for automated cert issuance",
            tech_stack=["Rust", "OpenSSL", "ACME"],
        )
        b = _make_idea(
            "ACME Certificate Authority",
            tagline="Automated X.509 cert issuance engine",
            description="A certificate authority using ACME protocol to issue and manage PKI certificates",
            tech_stack=["Go", "ACME", "x509"],
        )
        result = compare_ideas(a, b)
        assert result["overlap_score"] >= 0.4
        assert result["verdict"] in ("duplicate", "similar")

    def test_compare_unrelated_ideas_low_overlap(self):
        from project_forge.engine.compare import compare_ideas

        a = _make_idea(
            "SSH Honeypot Dashboard",
            tagline="Visualize attacker patterns",
            description="Real-time dashboard for SSH honeypot log analysis",
            tech_stack=["Python", "D3.js"],
            category=IdeaCategory.SECURITY_TOOL,
        )
        b = _make_idea(
            "NIST Compliance Checker",
            tagline="Audit NIST 800-53 controls",
            description="Automated compliance auditor for NIST special publications",
            tech_stack=["Go", "NIST"],
            category=IdeaCategory.COMPLIANCE,
        )
        result = compare_ideas(a, b)
        assert result["overlap_score"] < 0.3
        assert result["verdict"] == "distinct"

    def test_compare_ideas_winner_by_score(self):
        """Higher feasibility score should be the winner."""
        from project_forge.engine.compare import compare_ideas

        a = _make_idea("Idea A", score=0.9)
        b = _make_idea("Idea B", score=0.5)
        result = compare_ideas(a, b)
        assert result["winner"] == a.id

    def test_compare_ideas_returns_reason(self):
        from project_forge.engine.compare import compare_ideas

        a = _make_idea("Idea X", description="PKI certificate rotation automation")
        b = _make_idea("Idea Y", description="Cloud-native API gateway with rate limiting")
        result = compare_ideas(a, b)
        assert "reason" in result
        assert len(result["reason"]) > 0


# ============================================================
# 3. SELECTION ROUNDS — Model + DB
# ============================================================


class TestSelectionRoundModel:
    """SelectionRound Pydantic model."""

    def test_round_model_exists(self):
        from project_forge.models import SelectionRound

        sr = SelectionRound(
            round_number=2,
            idea_ids=["abc", "def", "ghi"],
        )
        assert sr.round_number == 2
        assert len(sr.idea_ids) == 3
        assert sr.id  # auto-generated
        assert sr.status == "pending"

    def test_round_status_values(self):
        from project_forge.models import SelectionRound

        sr = SelectionRound(round_number=1, idea_ids=["a", "b"])
        assert sr.status in ("pending", "in_progress", "completed")

    def test_round_has_results(self):
        from project_forge.models import SelectionRound

        sr = SelectionRound(
            round_number=2,
            idea_ids=["a", "b", "c"],
            results=[{"winner": "a", "loser": "b", "overlap": 0.6}],
        )
        assert len(sr.results) == 1

    def test_round_requires_at_least_two_ideas(self):
        from project_forge.models import SelectionRound

        with pytest.raises(ValidationError):
            SelectionRound(round_number=1, idea_ids=["only_one"])


class TestSelectionRoundDB:
    """SelectionRound persistence in SQLite."""

    @pytest.mark.asyncio
    async def test_save_round(self, db):
        from project_forge.models import SelectionRound

        ideas = [_make_idea(f"Round Idea {i}", score=0.5 + i * 0.1) for i in range(4)]
        for idea in ideas:
            await db.save_idea(idea)

        sr = SelectionRound(
            round_number=1,
            idea_ids=[i.id for i in ideas],
        )
        saved = await db.save_round(sr)
        assert saved.id == sr.id

    @pytest.mark.asyncio
    async def test_get_round(self, db):
        from project_forge.models import SelectionRound

        ideas = [_make_idea(f"Get-Round Idea {i}") for i in range(3)]
        for idea in ideas:
            await db.save_idea(idea)

        sr = SelectionRound(round_number=1, idea_ids=[i.id for i in ideas])
        await db.save_round(sr)

        fetched = await db.get_round(sr.id)
        assert fetched is not None
        assert fetched.round_number == 1
        assert set(fetched.idea_ids) == {i.id for i in ideas}

    @pytest.mark.asyncio
    async def test_list_rounds(self, db):
        from project_forge.models import SelectionRound

        ideas = [_make_idea(f"List-Round Idea {i}") for i in range(4)]
        for idea in ideas:
            await db.save_idea(idea)

        ids = [i.id for i in ideas]
        sr1 = SelectionRound(round_number=1, idea_ids=ids[:2])
        sr2 = SelectionRound(round_number=2, idea_ids=ids[2:])
        await db.save_round(sr1)
        await db.save_round(sr2)

        rounds = await db.list_rounds()
        assert len(rounds) == 2

    @pytest.mark.asyncio
    async def test_update_round_status(self, db):
        from project_forge.models import SelectionRound

        ideas = [_make_idea(f"Status Idea {i}") for i in range(2)]
        for idea in ideas:
            await db.save_idea(idea)

        sr = SelectionRound(round_number=1, idea_ids=[i.id for i in ideas])
        await db.save_round(sr)

        updated = await db.update_round_status(sr.id, "completed")
        assert updated.status == "completed"

    @pytest.mark.asyncio
    async def test_save_round_results(self, db):
        from project_forge.models import SelectionRound

        ideas = [_make_idea(f"Result Idea {i}", score=0.5 + i * 0.1) for i in range(3)]
        for idea in ideas:
            await db.save_idea(idea)

        sr = SelectionRound(round_number=1, idea_ids=[i.id for i in ideas])
        await db.save_round(sr)

        results = [
            {"idea_a": ideas[0].id, "idea_b": ideas[1].id, "winner": ideas[1].id, "overlap": 0.3},
            {"idea_a": ideas[1].id, "idea_b": ideas[2].id, "winner": ideas[2].id, "overlap": 0.2},
        ]
        updated = await db.save_round_results(sr.id, results)
        assert len(updated.results) == 2


# ============================================================
# 4. API ROUTES — Deny, Rounds, Comparisons
# ============================================================


@pytest_asyncio.fixture
async def round_client(tmp_path):
    from project_forge.web.app import app, db

    db.db_path = tmp_path / "test_rounds.db"
    await db.connect()

    # Seed 4 ideas
    ideas = [_make_idea(f"API Idea {i}", score=0.5 + i * 0.1) for i in range(4)]
    for idea in ideas:
        await db.save_idea(idea)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, ideas, db
    await db.close()


class TestDenyAPI:
    """POST /api/ideas/{id}/deny — deny with reason."""

    @pytest.mark.asyncio
    async def test_deny_with_reason(self, round_client):
        client, ideas, _ = round_client
        resp = await client.post(
            f"/api/ideas/{ideas[0].id}/deny",
            json={"reason": "Overlaps with pki-ca-engine"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "rejected"
        assert data["denial_id"]

    @pytest.mark.asyncio
    async def test_deny_requires_reason(self, round_client):
        client, ideas, _ = round_client
        resp = await client.post(
            f"/api/ideas/{ideas[0].id}/deny",
            json={},
        )
        assert resp.status_code == 422  # validation error

    @pytest.mark.asyncio
    async def test_deny_not_found(self, round_client):
        client, _, _ = round_client
        resp = await client.post(
            "/api/ideas/nonexistent/deny",
            json={"reason": "Does not exist"},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_deny_persists_to_db(self, round_client):
        client, ideas, test_db = round_client
        await client.post(
            f"/api/ideas/{ideas[1].id}/deny",
            json={"reason": "Market too crowded", "denied_by": "user:ray"},
        )
        denials = await test_db.get_denials(ideas[1].id)
        assert len(denials) == 1
        assert denials[0].reason == "Market too crowded"
        assert denials[0].denied_by == "user:ray"

    @pytest.mark.asyncio
    async def test_deny_sets_idea_status_rejected(self, round_client):
        client, ideas, test_db = round_client
        await client.post(
            f"/api/ideas/{ideas[2].id}/deny",
            json={"reason": "Not feasible"},
        )
        idea = await test_db.get_idea(ideas[2].id)
        assert idea.status == "rejected"


class TestRoundsAPI:
    """CRUD for selection rounds."""

    @pytest.mark.asyncio
    async def test_create_round(self, round_client):
        client, ideas, _ = round_client
        resp = await client.post(
            "/api/rounds",
            json={"idea_ids": [i.id for i in ideas[:3]]},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["round_number"] >= 1
        assert data["id"]
        assert len(data["idea_ids"]) == 3

    @pytest.mark.asyncio
    async def test_create_round_needs_two_ideas(self, round_client):
        client, ideas, _ = round_client
        resp = await client.post(
            "/api/rounds",
            json={"idea_ids": [ideas[0].id]},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_list_rounds(self, round_client):
        client, ideas, _ = round_client
        ids = [i.id for i in ideas]
        await client.post("/api/rounds", json={"idea_ids": ids[:2]})
        await client.post("/api/rounds", json={"idea_ids": ids[2:]})

        resp = await client.get("/api/rounds")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["rounds"]) == 2

    @pytest.mark.asyncio
    async def test_get_round(self, round_client):
        client, ideas, _ = round_client
        create_resp = await client.post(
            "/api/rounds",
            json={"idea_ids": [i.id for i in ideas[:3]]},
        )
        round_id = create_resp.json()["id"]

        resp = await client.get(f"/api/rounds/{round_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == round_id

    @pytest.mark.asyncio
    async def test_get_round_not_found(self, round_client):
        client, _, _ = round_client
        resp = await client.get("/api/rounds/nonexistent")
        assert resp.status_code == 404


class TestRoundCompareAPI:
    """Run comparisons within a selection round."""

    @pytest.mark.asyncio
    async def test_run_round_comparisons(self, round_client):
        """POST /api/rounds/{id}/compare runs all head-to-head matchups."""
        client, ideas, _ = round_client
        create_resp = await client.post(
            "/api/rounds",
            json={"idea_ids": [i.id for i in ideas[:3]]},
        )
        round_id = create_resp.json()["id"]

        resp = await client.post(f"/api/rounds/{round_id}/compare")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        # 3 ideas = 3 pairwise comparisons (3 choose 2)
        assert len(data["results"]) == 3
        # Each result should have winner, overlap, verdict
        for r in data["results"]:
            assert "idea_a" in r
            assert "idea_b" in r
            assert "winner" in r
            assert "overlap_score" in r
            assert "verdict" in r

    @pytest.mark.asyncio
    async def test_round_compare_persists_results(self, round_client):
        """Results should be saved back to the round in DB."""
        client, ideas, test_db = round_client
        create_resp = await client.post(
            "/api/rounds",
            json={"idea_ids": [i.id for i in ideas[:2]]},
        )
        round_id = create_resp.json()["id"]

        await client.post(f"/api/rounds/{round_id}/compare")

        sr = await test_db.get_round(round_id)
        assert sr.status == "completed"
        assert len(sr.results) == 1  # 2 ideas = 1 comparison

    @pytest.mark.asyncio
    async def test_round_compare_not_found(self, round_client):
        client, _, _ = round_client
        resp = await client.post("/api/rounds/nonexistent/compare")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_round_compare_denies_losers(self, round_client):
        """In a round, losing ideas with high overlap should get auto-denied."""
        client, ideas, test_db = round_client
        # Create two very similar ideas — one should lose
        similar_a = _make_idea(
            "PKI Cert Rotator A",
            score=0.9,
            tagline="Automate X.509 certificate rotation",
            description="PKI certificate rotation automation tool",
            tech_stack=["Rust"],
        )
        similar_b = _make_idea(
            "PKI Cert Rotator B",
            score=0.4,
            tagline="Automatic certificate rotation for PKI",
            description="Tool to automate PKI X.509 certificate rotation",
            tech_stack=["Rust"],
        )
        await test_db.save_idea(similar_a)
        await test_db.save_idea(similar_b)

        create_resp = await client.post(
            "/api/rounds",
            json={"idea_ids": [similar_a.id, similar_b.id]},
        )
        round_id = create_resp.json()["id"]

        resp = await client.post(f"/api/rounds/{round_id}/compare")
        data = resp.json()

        # The loser (lower score) should be auto-denied if overlap is high
        if data["results"][0]["overlap_score"] >= 0.4:
            result = data["results"][0]
            loser_id = result["idea_b"] if result["winner"] == similar_a.id else result["idea_a"]
            loser = await test_db.get_idea(loser_id)
            assert loser.status == "rejected"
            denials = await test_db.get_denials(loser_id)
            assert len(denials) >= 1
            assert "round" in denials[0].reason.lower() or "comparison" in denials[0].reason.lower()


# ============================================================
# 5. STATS INTEGRATION — Rounds in stats
# ============================================================


class TestStatsIntegration:
    @pytest.mark.asyncio
    async def test_stats_include_round_count(self, db):
        from project_forge.models import SelectionRound

        ideas = [_make_idea(f"Stats Idea {i}") for i in range(3)]
        for idea in ideas:
            await db.save_idea(idea)

        sr = SelectionRound(round_number=1, idea_ids=[i.id for i in ideas])
        await db.save_round(sr)

        stats = await db.get_stats()
        assert "total_rounds" in stats
        assert stats["total_rounds"] == 1

    @pytest.mark.asyncio
    async def test_stats_include_denial_count(self, db):
        from project_forge.models import IdeaDenial

        idea = _make_idea("Stats Denial Idea")
        await db.save_idea(idea)
        denial = IdeaDenial(idea_id=idea.id, reason="Test denial")
        await db.save_denial(denial)

        stats = await db.get_stats()
        assert "total_denials" in stats
        assert stats["total_denials"] == 1
