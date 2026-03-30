"""GitHub integration via gh CLI."""

import logging
import shlex
import subprocess

logger = logging.getLogger(__name__)


def _run_gh(args: list[str], cwd: str | None = None) -> str:
    """Run a gh CLI command and return stdout."""
    cmd = ["gh"] + args
    logger.info("Running: %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=60)
    if result.returncode != 0:
        logger.error("gh command failed: %s", result.stderr)
        raise RuntimeError(f"gh command failed: {result.stderr}")
    return result.stdout.strip()


def create_repo(name: str, description: str, public: bool = True) -> str:
    """Create a GitHub repo and return its URL."""
    args = ["repo", "create", f"rayketcham/{name}", f"--description={description}"]
    if public:
        args.append("--public")
    else:
        args.append("--private")
    url = _run_gh(args)
    logger.info("Created repo: %s", url)
    return url


def create_issue(repo: str, title: str, body: str, labels: list[str] | None = None) -> str:
    """Create a GitHub issue and return its URL."""
    safe_title = shlex.quote(title)
    safe_body = shlex.quote(body)
    args = ["issue", "create", "-R", repo, "--title", safe_title, "--body", safe_body]
    if labels:
        args.extend(["--label", ",".join(labels)])
    url = _run_gh(args)
    logger.info("Created issue: %s", url)
    return url


def create_label(repo: str, name: str, color: str, description: str = "") -> None:
    """Create a label on a GitHub repo."""
    args = ["label", "create", name, "-R", repo, "--color", color]
    if description:
        args.extend(["--description", description])
    try:
        _run_gh(args)
    except RuntimeError:
        logger.warning("Label %s may already exist on %s", name, repo)


def push_initial_commit(project_dir: str, remote_url: str) -> None:
    """Initialize git, commit all files, and push to remote."""
    cmds = [
        ["git", "init"],
        ["git", "branch", "-M", "main"],
        ["git", "add", "-A"],
        [
            "git",
            "commit",
            "-m",
            "Initial scaffold from Project Forge\n\nCo-Authored-By: Claude <noreply@anthropic.com>",
        ],
        ["git", "remote", "add", "origin", remote_url],
    ]
    for cmd in cmds:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_dir, timeout=30)
        if result.returncode != 0:
            raise RuntimeError(f"Git command failed: {' '.join(cmd)}: {result.stderr}")

    # Push with gh auth token
    result = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, timeout=10)
    token = result.stdout.strip()
    push_url = remote_url.replace("https://", f"https://rayketcham:{token}@")
    subprocess.run(
        ["git", "remote", "set-url", "origin", push_url],
        capture_output=True,
        text=True,
        cwd=project_dir,
        timeout=10,
    )
    result = subprocess.run(
        ["git", "push", "-u", "origin", "main"],
        capture_output=True,
        text=True,
        cwd=project_dir,
        timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Git push failed: {result.stderr}")
    # Clean up token from remote URL
    subprocess.run(
        ["git", "remote", "set-url", "origin", remote_url],
        capture_output=True,
        text=True,
        cwd=project_dir,
        timeout=10,
    )
    logger.info("Pushed initial commit to %s", remote_url)
