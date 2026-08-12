import html
import ipaddress
import re
import socket
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

import requests


@dataclass(frozen=True)
class WebSearchResult:
    title: str
    url: str
    snippet: str


_TAG_RE = re.compile(r"<[^>]+>")
_SCRIPT_STYLE_RE = re.compile(r"(?is)<(script|style)\b.*?>.*?</\1>")
_WHITESPACE_RE = re.compile(r"\s+")
_DDG_RESULT_A_RE = re.compile(r'(?is)<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>')
_DDG_SNIPPET_RE = re.compile(r'(?is)<a[^>]+class="result__snippet"[^>]*>(.*?)</a>')
_SEARX_ARTICLE_RE = re.compile(r'(?is)<article class="result.*?</article>')
_SEARX_H3_LINK_RE = re.compile(r'(?is)<h3>\s*<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>\s*</h3>')
_SEARX_SNIPPET_RE = re.compile(r'(?is)<p class="content[^"]*">(.*?)</p>')


def _normalize_domain(value: str) -> str:
    v = value.strip().lower()
    if v.startswith("."):
        v = v[1:]
    return v


def _domain_allowed(hostname: str, allowlist_domains: list[str]) -> bool:
    if not allowlist_domains:
        return True
    host = hostname.strip().lower().rstrip(".")
    for raw in allowlist_domains:
        d = _normalize_domain(raw)
        if not d:
            continue
        if host == d or host.endswith(f".{d}"):
            return True
    return False


def _is_public_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified:
        return False
    if ip.is_private:
        return False
    return True


def _hostname_resolves_to_public_ip(hostname: str) -> bool:
    try:
        infos = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
    except Exception:
        return False
    for info in infos:
        addr = info[4][0]
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            continue
        if not _is_public_ip(ip):
            return False
    return True


def _url_is_safe(url: str, allowlist_domains: list[str]) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False
    hostname = parsed.hostname
    if not hostname:
        return False
    if not _domain_allowed(hostname, allowlist_domains):
        return False
    return _hostname_resolves_to_public_ip(hostname)


def _html_to_text(value: str) -> str:
    cleaned = _SCRIPT_STYLE_RE.sub(" ", value)
    cleaned = _TAG_RE.sub(" ", cleaned)
    cleaned = html.unescape(cleaned)
    cleaned = _WHITESPACE_RE.sub(" ", cleaned).strip()
    return cleaned


def fetch_url_text(
    url: str,
    *,
    timeout_seconds: float,
    max_bytes: int,
    allowlist_domains: list[str],
) -> Optional[str]:
    if not _url_is_safe(url, allowlist_domains):
        return None
    try:
        with requests.get(
            url,
            timeout=timeout_seconds,
            stream=True,
            headers={"User-Agent": "ai-real-estate-assistant/1.0"},
        ) as resp:
            if resp.status_code != 200:
                return None
            content_type = (resp.headers.get("content-type") or "").lower()
            raw = resp.raw.read(max_bytes + 1, decode_content=True)
            if len(raw) > max_bytes:
                return None
            text = raw.decode(resp.encoding or "utf-8", errors="replace")
            if "html" in content_type:
                return _html_to_text(text)
            if "text/plain" in content_type or content_type.startswith("text/"):
                return _WHITESPACE_RE.sub(" ", text).strip()
            return None
    except Exception:
        return None


def searxng_search(
    *,
    searxng_url: str,
    query: str,
    max_results: int,
    timeout_seconds: float,
) -> list[WebSearchResult]:
    base = searxng_url.rstrip("/")
    params = {
        "q": query,
    }
    headers = {
        "User-Agent": "ai-real-estate-assistant/1.0",
        "X-Forwarded-For": "1.1.1.1",
        "X-Real-IP": "1.1.1.1",
    }
    try:
        resp = requests.get(
            f"{base}/search", params=params, timeout=timeout_seconds, headers=headers
        )
        if resp.status_code != 200:
            return []
        html_text = resp.text or ""
        articles = _SEARX_ARTICLE_RE.findall(html_text)
        results: list[WebSearchResult] = []
        for article in articles[: max(0, int(max_results))]:
            m = _SEARX_H3_LINK_RE.search(article)
            if not m:
                continue
            url = m.group(1).strip()
            title = _html_to_text(m.group(2))
            snippet_match = _SEARX_SNIPPET_RE.search(article)
            snippet = _html_to_text(snippet_match.group(1)) if snippet_match else ""
            if not url:
                continue
            results.append(WebSearchResult(title=title, url=url, snippet=snippet))
        return results
    except Exception:
        return []


def duckduckgo_html_search(
    *,
    query: str,
    max_results: int,
    timeout_seconds: float,
) -> list[WebSearchResult]:
    params = {"q": query}
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(
            "https://duckduckgo.com/html/", params=params, headers=headers, timeout=timeout_seconds
        )
        if resp.status_code not in {200, 202}:
            return []
        html_text = resp.text or ""
        anchors = list(_DDG_RESULT_A_RE.finditer(html_text))
        snippets = list(_DDG_SNIPPET_RE.finditer(html_text))

        results: list[WebSearchResult] = []
        for idx, m in enumerate(anchors[: max(0, int(max_results))]):
            url = m.group(1).strip()
            title = _html_to_text(m.group(2))
            snippet = ""
            if idx < len(snippets):
                snippet = _html_to_text(snippets[idx].group(1))
            if not url:
                continue
            results.append(WebSearchResult(title=title, url=url, snippet=snippet))
        return results
    except Exception:
        return []


def serpbase_search(
    *,
    api_key: str,
    query: str,
    max_results: int,
    timeout_seconds: float,
) -> list[WebSearchResult]:
    """Search Google via the SerpBase REST API (https://serpbase.dev).

    Returns an empty list on any error so callers can fall back to other
    backends. Requires a SerpBase API key; callers without one should not
    call this function (WebSearchTool only does when SERPBASE_API_KEY is set).
    """
    if not api_key:
        return []
    params = {
        "q": query,
        "api_key": api_key,
        "num": str(max(1, min(int(max_results), 20))),
    }
    headers = {"User-Agent": "ai-real-estate-assistant/1.0"}
    try:
        resp = requests.get(
            "https://api.serpbase.dev/google/search",
            params=params,
            headers=headers,
            timeout=timeout_seconds,
        )
        if resp.status_code != 200:
            return []
        payload = resp.json()
        results: list[WebSearchResult] = []
        for item in (payload.get("organic_results") or [])[: max(0, int(max_results))]:
            url = str(item.get("link") or "").strip()
            if not url:
                continue
            results.append(
                WebSearchResult(
                    title=str(item.get("title") or "").strip(),
                    url=url,
                    snippet=str(item.get("snippet") or "").strip(),
                )
            )
        return results
    except Exception:
        return []
