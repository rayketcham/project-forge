"""Tests for dashboard tabs — Ideas, Super Ideas, and Add Idea."""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from project_forge.cron.auto_scan import run_auto_scan
from project_forge.engine.super_ideas import SuperIdeaGenerator
from project_forge.web.app import app, db


@pytest_asyncio.fixture
async def client(tmp_path):
    db.db_path = tmp_path / "test_tabs.db"
    await db.connect()
    # Seed enough ideas for super idea generation
    await run_auto_scan(db, count=50)
    gen = SuperIdeaGenerator(db)
    await gen.generate(count=3)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    await db.close()


class TestDashboardTabs:
    """Dashboard should have tab navigation for Ideas, Super Ideas, Add Idea."""

    @pytest.mark.asyncio
    async def test_dashboard_has_tab_bar(self, client):
        resp = await client.get("/")
        assert resp.status_code == 200
        assert 'class="tab-bar"' in resp.text

    @pytest.mark.asyncio
    async def test_dashboard_has_ideas_tab(self, client):
        resp = await client.get("/")
        assert 'data-tab="ideas"' in resp.text

    @pytest.mark.asyncio
    async def test_dashboard_has_super_ideas_tab(self, client):
        resp = await client.get("/")
        assert 'data-tab="super-ideas"' in resp.text

    @pytest.mark.asyncio
    async def test_dashboard_has_add_idea_tab(self, client):
        resp = await client.get("/")
        assert 'data-tab="add-idea"' in resp.text

    @pytest.mark.asyncio
    async def test_ideas_tab_panel_exists(self, client):
        resp = await client.get("/")
        assert 'id="tab-ideas"' in resp.text

    @pytest.mark.asyncio
    async def test_super_ideas_tab_panel_exists(self, client):
        resp = await client.get("/")
        assert 'id="tab-super-ideas"' in resp.text

    @pytest.mark.asyncio
    async def test_add_idea_tab_panel_exists(self, client):
        resp = await client.get("/")
        assert 'id="tab-add-idea"' in resp.text


class TestSuperIdeasOnDashboard:
    """Super ideas should be shown in their own tab panel."""

    @pytest.mark.asyncio
    async def test_super_ideas_passed_to_template(self, client):
        """The dashboard should display [SUPER] ideas."""
        resp = await client.get("/")
        assert "[SUPER]" in resp.text

    @pytest.mark.asyncio
    async def test_super_ideas_have_cards(self, client):
        resp = await client.get("/")
        assert 'class="idea-card"' in resp.text


class TestAddIdeaInTab:
    """The URL ingest form should be in the Add Idea tab, not floating."""

    @pytest.mark.asyncio
    async def test_url_input_in_add_tab(self, client):
        resp = await client.get("/")
        html = resp.text
        assert 'id="url-input"' in html
        assert 'id="tab-add-idea"' in html

    @pytest.mark.asyncio
    async def test_add_tab_has_url_submit(self, client):
        resp = await client.get("/")
        assert 'id="url-submit-btn"' in resp.text


class TestTabSwitchingJS:
    """JavaScript should handle tab switching."""

    @pytest.mark.asyncio
    async def test_app_js_has_tab_switch_function(self, client):
        resp = await client.get("/static/app.js")
        assert "switchTab" in resp.text
