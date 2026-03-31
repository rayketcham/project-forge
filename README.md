# Project Forge

**Autonomous IT project think-tank engine.** Generates novel project ideas across 12 security-focused categories, scores feasibility, synthesizes cross-domain "super ideas," and scaffolds the best ones into real GitHub repos with CI/CD pipelines — all without human intervention.

Built with Python 3.12, FastAPI, SQLite, and the Anthropic SDK.

---

## How It Works

```
Seed Concepts + Domains + Directions
        |
        v
  Auto-Scan Engine -----> Ideas (scored 0-1)
        |                      |
        v                      v
  Super Idea Synthesis    Compare to Existing Repos
        |                      |
        v                      v
  Dashboard (approve/reject/scaffold)
        |
        v
  GitHub Repo + CI + Issues
```

1. **Generate** -- The engine crosses seed concepts with domains using four generation directions (basic, contrarian, combinatoric, crossover) to produce diverse project ideas. Input-tuple tracking prevents regenerating the same combinations.
2. **Score** -- Each idea is scored on market timing, competition landscape, and MVP complexity (0.0-1.0).
3. **Synthesize** -- The Super Ideas engine clusters related ideas across categories and synthesizes ambitious cross-domain mega-projects.
4. **Compare** -- Before building, compare any idea against existing org repos to decide: enhance an existing project, or build something new.
5. **Scaffold** -- Approved ideas get a real GitHub repo with language-appropriate project structure, CI/CD pipeline, test scaffolding, and initial issues.

---

## Features

| Feature | Description |
|---------|-------------|
| **Idea Generation** | Claude-powered + local auto-scan engine producing ideas across 12 categories |
| **Feasibility Scoring** | Market timing, competition, MVP complexity -- scored 0.0 to 1.0 |
| **Super Ideas** | Cross-category synthesis into ambitious mega-projects with phased MVPs |
| **Compare to Repo** | Keyword overlap analysis against existing GitHub repos -- duplicate, enhance, or new? |
| **Auto-Scaffolding** | GitHub repo creation with CI, tests, README, and starter issues |
| **Dedup Engine** | Content fingerprinting + input-tuple tracking prevents duplicate ideas at scale |
| **Web Dashboard** | Browse, search, filter, approve, reject, scaffold -- all from the browser |
| **Autonomous Mode** | Cron-driven generation with no human intervention required |

---

## Categories

| Category | Focus Area |
|----------|-----------|
| `pqc-cryptography` | Post-quantum cryptographic algorithms and migration tooling |
| `nist-standards` | NIST framework compliance, FIPS validation, SP 800 series |
| `rfc-security` | IETF RFC implementation for security protocols |
| `crypto-infrastructure` | PKI, certificate management, key lifecycle |
| `security-tool` | Offensive and defensive security toolchain gaps |
| `vulnerability-research` | Novel vulnerability discovery and analysis |
| `privacy` | Privacy-preserving technologies and PETs |
| `compliance` | Regulatory compliance automation (SOC2, FedRAMP, CMMC) |
| `observability` | Security monitoring, logging, anomaly detection |
| `devops-tooling` | Developer experience and infrastructure security |
| `automation` | Workflow and process automation |
| `market-gap` | Products and services missing from the market |

---

## Quick Start

```bash
# Clone and install
git clone https://github.com/rayketcham-lab/project-forge.git
cd project-forge
pip install -e ".[dev,test]"

# Run tests
pytest tests/ -v

# Lint
ruff check src/ tests/

# Start the dashboard
python -m uvicorn project_forge.web.app:app --host 0.0.0.0 --port 55443

# Generate ideas (auto-scan, no API key needed)
python -m project_forge.cron.runner
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `FORGE_ANTHROPIC_API_KEY` | -- | Claude API key (optional -- auto-scan works without it) |
| `FORGE_DB_PATH` | `data/forge.db` | SQLite database path |
| `FORGE_PORT` | `55443` | Web dashboard port |
| `FORGE_GITHUB_OWNER` | `rayketcham-lab` | Default GitHub org for scaffolding |

---

## Architecture

```
src/project_forge/
  config.py              # pydantic-settings configuration
  models.py              # Pydantic models (Idea, ScaffoldSpec, GenerationRun)
  engine/
    categories.py        # 12 category seed definitions
    generator.py         # Claude-powered idea generation
    scorer.py            # Feasibility scoring
    compare.py           # Idea-to-repo comparison engine
    super_ideas.py       # Cross-category mega-project synthesis
    prompts.py           # Prompt templates for all generation modes
  storage/
    db.py                # SQLite with WAL mode, content dedup, tuple tracking
  web/
    app.py               # FastAPI application
    routes.py            # Dashboard + REST API endpoints
    templates/           # Jinja2 HTML templates
    static/              # CSS + JavaScript
  scaffold/
    builder.py           # Project structure generation
    github.py            # GitHub CLI integration (repo, issues, labels)
    templates/           # Jinja2 scaffolding templates
  cron/
    runner.py            # Entry point for autonomous generation
    scheduler.py         # Full cycle orchestration
    auto_scan.py         # Local generation (no API key required)
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Dashboard with stats, top ideas, categories |
| `GET` | `/explore` | Browse/filter/search all ideas |
| `GET` | `/ideas/{id}` | Idea detail with compare-to-repo |
| `POST` | `/ideas/{id}/approve` | Approve an idea |
| `POST` | `/ideas/{id}/reject` | Reject an idea |
| `POST` | `/ideas/{id}/scaffold` | Scaffold to GitHub repo |
| `GET` | `/api/repos` | List org repos (for compare dropdown) |
| `POST` | `/api/ideas/{id}/compare` | Compare idea against a repo |
| `GET` | `/api/stats` | Dashboard statistics |
| `GET` | `/api/search?q=` | Search ideas |
| `GET` | `/health` | Health check |

---

## Tech Stack

- **Python 3.12** -- Modern syntax, StrEnum, match/case
- **FastAPI** -- Async web framework with Jinja2 templates
- **SQLite** -- WAL mode, content hash dedup, input-tuple tracking
- **Anthropic SDK** -- Claude Sonnet for idea generation (optional)
- **GitHub CLI** -- Repo creation, issue management, scaffolding
- **Ruff** -- Linting and formatting
- **pytest** -- 175+ tests with pytest-asyncio

---

## License

MIT
