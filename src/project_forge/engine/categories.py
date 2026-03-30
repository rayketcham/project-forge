"""Category definitions and seed concepts for diverse idea generation."""

from project_forge.models import IdeaCategory

CATEGORY_SEEDS: dict[IdeaCategory, dict] = {
    IdeaCategory.SECURITY_TOOL: {
        "description": "Tools that fill gaps in the security toolchain",
        "seed_concepts": [
            "supply chain attack detection",
            "runtime memory forensics",
            "API key rotation automation",
            "zero-trust micro-segmentation",
            "firmware integrity verification",
            "secrets sprawl detection across repos",
            "lateral movement detection in containerized environments",
            "post-quantum cryptography migration tools",
        ],
        "domains_to_cross": ["healthcare", "IoT", "automotive", "fintech", "gaming"],
    },
    IdeaCategory.MARKET_GAP: {
        "description": "Products or services missing from the market",
        "seed_concepts": [
            "developer tool fatigue aggregator",
            "technical debt quantification platform",
            "open-source sustainability metrics",
            "cross-cloud cost anomaly detection",
            "infrastructure archaeology for legacy systems",
            "compliance-as-code marketplace",
            "developer onboarding time-to-first-commit optimizer",
            "SaaS feature usage dead code detector",
        ],
        "domains_to_cross": ["education", "government", "nonprofit", "logistics", "agriculture"],
    },
    IdeaCategory.VULNERABILITY_RESEARCH: {
        "description": "Novel vulnerability discovery and analysis approaches",
        "seed_concepts": [
            "LLM prompt injection fuzzer",
            "smart contract formal verification",
            "protocol-level timing attack detector",
            "browser extension permission abuse scanner",
            "CI/CD pipeline privilege escalation finder",
            "GraphQL introspection exploit kit",
            "WebAssembly sandbox escape detector",
            "DNS rebinding attack surface mapper",
        ],
        "domains_to_cross": ["embedded systems", "satellites", "medical devices", "voting systems", "robotics"],
    },
    IdeaCategory.AUTOMATION: {
        "description": "Workflow and process automation that saves real time",
        "seed_concepts": [
            "incident response runbook executor",
            "regulatory change impact assessor",
            "meeting-to-ticket pipeline",
            "cross-team dependency conflict resolver",
            "automated architecture decision records",
            "changelog-to-migration-guide generator",
            "stale documentation detector and updater",
            "test environment provisioning orchestrator",
        ],
        "domains_to_cross": ["legal", "real estate", "insurance", "manufacturing", "energy"],
    },
    IdeaCategory.DEVOPS_TOOLING: {
        "description": "Developer experience and infrastructure tools",
        "seed_concepts": [
            "deployment rollback confidence scorer",
            "infrastructure drift detector with fix suggestions",
            "multi-cloud service mesh visualizer",
            "CI pipeline bottleneck profiler",
            "ephemeral environment cost optimizer",
            "feature flag lifecycle manager",
            "database migration risk assessor",
            "service dependency graph auto-documenter",
        ],
        "domains_to_cross": ["edge computing", "serverless", "bare metal", "hybrid cloud", "on-prem"],
    },
    IdeaCategory.PRIVACY: {
        "description": "Privacy-preserving technologies and tools",
        "seed_concepts": [
            "PII detection in unstructured data streams",
            "differential privacy budget tracker",
            "consent management for microservices",
            "data lineage tracker across distributed systems",
            "synthetic data generation with privacy guarantees",
            "browser fingerprinting resistance tester",
            "cross-border data flow compliance mapper",
            "privacy impact assessment automation",
        ],
        "domains_to_cross": ["children's data", "biometrics", "location tracking", "health records", "financial data"],
    },
    IdeaCategory.COMPLIANCE: {
        "description": "Regulatory compliance automation and monitoring",
        "seed_concepts": [
            "SOC 2 evidence collection automation",
            "SBOM generation and vulnerability tracking",
            "access review automation with anomaly detection",
            "audit trail immutability verification",
            "policy-as-code enforcement engine",
            "third-party vendor risk continuous monitoring",
            "license compliance for transitive dependencies",
            "data retention policy enforcer",
        ],
        "domains_to_cross": ["HIPAA", "FedRAMP", "GDPR", "PCI-DSS", "CMMC"],
    },
    IdeaCategory.OBSERVABILITY: {
        "description": "Monitoring, logging, and tracing innovations",
        "seed_concepts": [
            "cost-aware log sampling engine",
            "trace-based testing framework",
            "anomaly detection for distributed traces",
            "SLO burn rate predictor",
            "customer-facing status page from internal metrics",
            "log-to-metric automatic converter",
            "observability data deduplication engine",
            "cross-service error correlation mapper",
        ],
        "domains_to_cross": ["mobile apps", "CLI tools", "batch jobs", "real-time systems", "ML pipelines"],
    },
}

COMBINATORIC_TEMPLATES = [
    "What if {concept_a} was applied to {domain_b}?",
    "What tool would you need if {concept_a} and {concept_b} had to work together?",
    "What's the opposite of {concept_a} -- and would building that be valuable?",
    "If {domain_a} had the same tooling maturity as {domain_b}, what would exist that doesn't today?",
    "What breaks first when {concept_a} scales to 10x its current usage?",
]

CONTRARIAN_PROMPTS = [
    "What security problem does everyone ignore because they think it's already solved?",
    "What developer tool is everyone building wrong because they copied the first implementation?",
    "What compliance requirement is actually an opportunity disguised as a burden?",
    "What monitoring gap only becomes visible during an incident -- but could be caught proactively?",
    "What problem is getting worse faster than the current solutions can keep up with?",
    "What would a startup build if they had zero legacy constraints but deep domain expertise?",
    "What tool do teams build internally over and over because no good open-source version exists?",
    "What's the 'spreadsheet that should be a product' in your domain?",
]
