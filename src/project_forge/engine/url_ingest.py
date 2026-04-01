"""URL ingestion engine — fetch URLs, extract content, generate ideas."""

import ipaddress
import re
import socket
from dataclasses import dataclass
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

# Tracking parameters to strip from URLs
TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_content",
    "utm_term",
    "ref",
    "fbclid",
    "gclid",
}


class UrlFetchError(Exception):
    """Raised when a URL cannot be fetched successfully."""


@dataclass
class UrlContent:
    url: str
    domain: str
    title: str
    text: str


def _check_ssrf(hostname: str) -> None:
    """Resolve hostname and raise ValueError if it resolves to a private/reserved address.

    Protects against Server-Side Request Forgery (SSRF) by blocking requests
    to loopback, private, link-local, and other reserved IP ranges.

    Raises:
        ValueError: If the hostname resolves to a non-public IP address.
        socket.gaierror: If the hostname cannot be resolved (propagated to caller).
    """
    try:
        addrinfos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        # DNS resolution failure — not a private IP issue; let caller handle
        raise

    for addrinfo in addrinfos:
        raw_ip = addrinfo[4][0]
        try:
            addr = ipaddress.ip_address(raw_ip)
        except ValueError:
            continue
        if addr.is_loopback or addr.is_private or addr.is_link_local or addr.is_reserved:
            raise ValueError(f"Requests to private/reserved addresses are not allowed: {raw_ip}")


def validate_url(url: str) -> bool:
    """Check if URL is valid http(s) and does not point to a private/reserved address.

    Returns:
        True if the URL is structurally valid and resolves to a public address.

    Raises:
        ValueError: If the URL resolves to a private, loopback, or link-local IP (SSRF guard).
    """
    if not url:
        return False
    try:
        parsed = urlparse(url)
        if not (parsed.scheme in ("http", "https") and bool(parsed.netloc)):
            return False
    except Exception:
        return False

    # Strip port from netloc to get bare hostname for DNS resolution
    hostname = parsed.hostname
    if not hostname:
        return False

    # For bare IP addresses, validate directly without a DNS lookup
    try:
        addr = ipaddress.ip_address(hostname)
        if addr.is_loopback or addr.is_private or addr.is_link_local or addr.is_reserved:
            raise ValueError(f"Requests to private/reserved addresses are not allowed: {hostname}")
        return True
    except ValueError as exc:
        # Re-raise only the SSRF guard errors; ignore the "not a valid IP" parse error
        if "not allowed" in str(exc):
            raise

    # Hostname is not a bare IP — resolve via DNS
    _check_ssrf(hostname)
    return True


def extract_domain(url: str) -> str:
    """Extract clean domain from URL (strip www.)."""
    parsed = urlparse(url)
    domain = parsed.netloc
    if domain.startswith("www."):
        domain = domain[4:]
    return domain


def clean_url(url: str) -> str:
    """Remove tracking parameters from URL."""
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    clean_params = {k: v for k, v in params.items() if k not in TRACKING_PARAMS}
    if clean_params:
        clean_query = urlencode(clean_params, doseq=True)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{clean_query}"
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"


async def fetch_url_content(url: str) -> UrlContent:
    """Fetch URL and extract content.

    Validates the URL for SSRF safety before making any network request.
    Redirects are disabled to prevent redirect-based SSRF bypasses.

    Raises:
        ValueError: If the URL resolves to a private/reserved address.
        UrlFetchError: If the HTTP response indicates an error (status >= 400).
    """
    # SSRF guard — must run before any network I/O
    validate_url(url)

    async with httpx.AsyncClient(follow_redirects=False, timeout=30.0) as client:
        response = await client.get(url)

    if response.status_code >= 400:
        raise UrlFetchError(f"HTTP {response.status_code} fetching {url}")

    text = response.text
    domain = extract_domain(url)

    # Extract title from HTML and strip tags for text content
    title = ""
    content_type = response.headers.get("content-type", "")
    if "html" in content_type:
        title_match = re.search(r"<title[^>]*>(.*?)</title>", text, re.DOTALL | re.IGNORECASE)
        if title_match:
            title = title_match.group(1).strip()
        # Strip script/style blocks first, then all other tags
        text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()

    if not title:
        title = domain  # Fallback to domain when no HTML title found

    return UrlContent(url=url, domain=domain, title=title, text=text[:5000])


async def generate_idea_from_url(content: UrlContent, category_hint: str | None = None):
    """Generate an idea from URL content via IdeaGenerator."""
    from project_forge.engine.generator import IdeaGenerator

    content.url = clean_url(content.url)
    generator = IdeaGenerator()
    idea = await generator.generate_from_content(content, category_hint=category_hint)
    return idea
