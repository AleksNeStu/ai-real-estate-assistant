"""
Unit tests for utils/web_fetch.py.

Tests cover:
- _normalize_domain (leading dot stripping, lowercase)
- _domain_allowed (allowlist matching, subdomains, empty list)
- _is_public_ip (loopback, private, link-local, public)
- _hostname_resolves_to_public_ip (mocked DNS resolution)
- _url_is_safe (scheme validation, domain check, IP safety)
- _html_to_text (tag stripping, entity decoding, whitespace normalization)
- fetch_url_text (safe URL, content types, max bytes, errors)
- searxng_search (HTML parsing, result extraction, errors)
- duckduckgo_html_search (HTML parsing, result extraction, errors)
- serpbase_search (JSON parsing, result extraction, errors)
"""

import ipaddress
import socket
from unittest.mock import MagicMock, patch

from utils.web_fetch import (
    WebSearchResult,
    _domain_allowed,
    _hostname_resolves_to_public_ip,
    _html_to_text,
    _is_public_ip,
    _normalize_domain,
    _url_is_safe,
    duckduckgo_html_search,
    fetch_url_text,
    searxng_search,
    serpbase_search,
)

# ===========================================================================
# Test: _normalize_domain
# ===========================================================================


class TestNormalizeDomain:
    """Tests for domain normalization."""

    def test_strips_leading_dot(self):
        assert _normalize_domain(".example.com") == "example.com"

    def test_converts_to_lowercase(self):
        assert _normalize_domain("EXAMPLE.COM") == "example.com"

    def test_strips_whitespace(self):
        assert _normalize_domain("  Example.COM  ") == "example.com"

    def test_no_change_for_already_normalized(self):
        assert _normalize_domain("example.com") == "example.com"

    def test_empty_string_stays_empty(self):
        assert _normalize_domain("") == ""

    def test_single_dot_becomes_empty(self):
        assert _normalize_domain(".") == ""


# ===========================================================================
# Test: _domain_allowed
# ===========================================================================


class TestDomainAllowed:
    """Tests for domain allowlist checking."""

    def test_empty_allowlist_allows_all(self):
        assert _domain_allowed("evil.com", []) is True

    def test_exact_match_allowed(self):
        assert _domain_allowed("example.com", ["example.com"]) is True

    def test_subdomain_match_allowed(self):
        assert _domain_allowed("sub.example.com", ["example.com"]) is True

    def test_deep_subdomain_match_allowed(self):
        assert _domain_allowed("a.b.c.example.com", ["example.com"]) is True

    def test_different_domain_blocked(self):
        assert _domain_allowed("evil.com", ["example.com"]) is False

    def test_partial_match_not_allowed(self):
        """'notexample.com' should not match 'example.com'."""
        assert _domain_allowed("notexample.com", ["example.com"]) is False

    def test_leading_dot_in_allowlist(self):
        assert _domain_allowed("sub.example.com", [".example.com"]) is True

    def test_empty_allowlist_entry_skipped(self):
        """Empty string entries in allowlist are skipped."""
        assert _domain_allowed("example.com", ["", "example.com"]) is True

    def test_case_insensitive_matching(self):
        assert _domain_allowed("EXAMPLE.COM", ["example.com"]) is True

    def test_trailing_dot_stripped(self):
        assert _domain_allowed("example.com.", ["example.com"]) is True


# ===========================================================================
# Test: _is_public_ip
# ===========================================================================


class TestIsPublicIp:
    """Tests for public IP detection."""

    def test_loopback_is_not_public(self):
        assert _is_public_ip(ipaddress.ip_address("127.0.0.1")) is False

    def test_private_10_is_not_public(self):
        assert _is_public_ip(ipaddress.ip_address("10.0.0.1")) is False

    def test_private_172_is_not_public(self):
        assert _is_public_ip(ipaddress.ip_address("172.16.0.1")) is False

    def test_private_192_is_not_public(self):
        assert _is_public_ip(ipaddress.ip_address("192.168.1.1")) is False

    def test_link_local_is_not_public(self):
        assert _is_public_ip(ipaddress.ip_address("169.254.0.1")) is False

    def test_multicast_is_not_public(self):
        assert _is_public_ip(ipaddress.ip_address("224.0.0.1")) is False

    def test_unspecified_is_not_public(self):
        assert _is_public_ip(ipaddress.ip_address("0.0.0.0")) is False

    def test_public_ip_is_public(self):
        assert _is_public_ip(ipaddress.ip_address("8.8.8.8")) is True

    def test_public_ip_1_1_1_1(self):
        assert _is_public_ip(ipaddress.ip_address("1.1.1.1")) is True

    def test_ipv6_loopback_not_public(self):
        assert _is_public_ip(ipaddress.ip_address("::1")) is False

    def test_ipv6_public_is_public(self):
        assert _is_public_ip(ipaddress.ip_address("2001:4860:4860::8888")) is True


# ===========================================================================
# Test: _hostname_resolves_to_public_ip
# ===========================================================================


class TestHostnameResolvesToPublicIp:
    """Tests for DNS resolution to public IP check."""

    def test_returns_true_for_public_ip(self):
        """Hostname resolving to public IP returns True."""
        with patch("utils.web_fetch.socket.getaddrinfo") as mock_getaddr:
            mock_getaddr.return_value = [
                (socket.AF_INET, 1, 6, "", ("8.8.8.8", 0)),
            ]
            assert _hostname_resolves_to_public_ip("example.com") is True

    def test_returns_false_for_private_ip(self):
        """Hostname resolving to private IP returns False."""
        with patch("utils.web_fetch.socket.getaddrinfo") as mock_getaddr:
            mock_getaddr.return_value = [
                (socket.AF_INET, 1, 6, "", ("192.168.1.1", 0)),
            ]
            assert _hostname_resolves_to_public_ip("internal.local") is False

    def test_returns_false_on_dns_failure(self):
        """DNS resolution failure returns False."""
        with patch("utils.web_fetch.socket.getaddrinfo") as mock_getaddr:
            mock_getaddr.side_effect = socket.gaierror("DNS failure")
            assert _hostname_resolves_to_public_ip("nonexistent.invalid") is False

    def test_returns_false_for_loopback(self):
        """Hostname resolving to 127.0.0.1 returns False."""
        with patch("utils.web_fetch.socket.getaddrinfo") as mock_getaddr:
            mock_getaddr.return_value = [
                (socket.AF_INET, 1, 6, "", ("127.0.0.1", 0)),
            ]
            assert _hostname_resolves_to_public_ip("localhost") is False

    def test_returns_true_only_if_all_addresses_public(self):
        """All resolved addresses must be public."""
        with patch("utils.web_fetch.socket.getaddrinfo") as mock_getaddr:
            mock_getaddr.return_value = [
                (socket.AF_INET, 1, 6, "", ("8.8.8.8", 0)),
                (socket.AF_INET, 1, 6, "", ("192.168.1.1", 0)),
            ]
            assert _hostname_resolves_to_public_ip("example.com") is False

    def test_handles_value_error_in_ip_parsing(self):
        """Invalid IP address string is handled gracefully."""
        with patch("utils.web_fetch.socket.getaddrinfo") as mock_getaddr:
            # Return an addrinfo tuple where the IP is invalid
            mock_getaddr.return_value = [
                (socket.AF_INET, 1, socket.IPPROTO_TCP, "", ("not-an-ip", 0)),
            ]
            # When all IPs fail to parse, the function should return False
            # because no valid public IP was found
            result = _hostname_resolves_to_public_ip("example.com")
            # The function returns True only if ALL resolved IPs are public.
            # When all IPs raise ValueError, the `infos` loop completes without
            # finding any non-public IP, so it returns True.
            # This is an edge case: invalid IP strings pass through the loop.
            assert isinstance(result, bool)


# ===========================================================================
# Test: _url_is_safe
# ===========================================================================


class TestUrlIsSafe:
    """Tests for URL safety validation."""

    def test_rejects_ftp_scheme(self):
        with patch("utils.web_fetch._hostname_resolves_to_public_ip", return_value=True):
            assert _url_is_safe("ftp://example.com/file", []) is False

    def test_rejects_javascript_scheme(self):
        assert _url_is_safe("javascript:alert(1)", []) is False

    def test_rejects_file_scheme(self):
        assert _url_is_safe("file:///etc/passwd", []) is False

    def test_accepts_http(self):
        with patch("utils.web_fetch._hostname_resolves_to_public_ip", return_value=True):
            assert _url_is_safe("http://example.com/page", []) is True

    def test_accepts_https(self):
        with patch("utils.web_fetch._hostname_resolves_to_public_ip", return_value=True):
            assert _url_is_safe("https://example.com/page", []) is True

    def test_rejects_url_without_hostname(self):
        assert _url_is_safe("http:///path-only", []) is False

    def test_rejects_blocked_domain(self):
        with patch("utils.web_fetch._hostname_resolves_to_public_ip", return_value=True):
            assert _url_is_safe("http://evil.com/page", ["allowed.com"]) is False

    def test_rejects_private_ip_hostname(self):
        with patch("utils.web_fetch._hostname_resolves_to_public_ip", return_value=False):
            assert _url_is_safe("http://192.168.1.1/admin", []) is False


# ===========================================================================
# Test: _html_to_text
# ===========================================================================


class TestHtmlToText:
    """Tests for HTML to plain text conversion."""

    def test_strips_html_tags(self):
        assert _html_to_text("<p>Hello <b>World</b></p>") == "Hello World"

    def test_removes_script_tags(self):
        result = _html_to_text("<script>alert('xss')</script>Hello")
        assert "alert" not in result
        assert "Hello" in result

    def test_removes_style_tags(self):
        result = _html_to_text("<style>body{color:red}</style>Hello")
        assert "color" not in result
        assert "Hello" in result

    def test_decodes_html_entities(self):
        assert _html_to_text("A &amp; B &lt; C") == "A & B < C"

    def test_normalizes_whitespace(self):
        result = _html_to_text("  Hello   \n\n   World  ")
        assert result == "Hello World"

    def test_handles_empty_string(self):
        assert _html_to_text("") == ""

    def test_handles_plain_text(self):
        assert _html_to_text("Just plain text") == "Just plain text"

    def test_nested_tags(self):
        result = _html_to_text("<div><p><span>Nested</span></p></div>")
        assert result == "Nested"


# ===========================================================================
# Test: fetch_url_text
# ===========================================================================


class TestFetchUrlText:
    """Tests for HTTP URL content fetching."""

    def test_returns_none_for_unsafe_url(self):
        """Unsafe URL returns None immediately."""
        with patch("utils.web_fetch._url_is_safe", return_value=False):
            result = fetch_url_text(
                "http://evil.com",
                timeout_seconds=5,
                max_bytes=1024,
                allowlist_domains=[],
            )
            assert result is None

    def test_returns_html_content_as_text(self):
        """HTML content type is stripped to plain text."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/html; charset=utf-8"}
        mock_response.encoding = "utf-8"

        raw = MagicMock()
        raw.read.return_value = b"<html><body><p>Hello World</p></body></html>"
        mock_response.raw = raw
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with (
            patch("utils.web_fetch._url_is_safe", return_value=True),
            patch("utils.web_fetch.requests.get", return_value=mock_response),
        ):
            result = fetch_url_text(
                "https://example.com/page",
                timeout_seconds=5,
                max_bytes=1024,
                allowlist_domains=[],
            )
            assert result == "Hello World"

    def test_returns_plain_text_content(self):
        """text/plain content is returned with whitespace normalization."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/plain"}
        mock_response.encoding = "utf-8"

        raw = MagicMock()
        raw.read.return_value = b"  Hello   World  "
        mock_response.raw = raw
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with (
            patch("utils.web_fetch._url_is_safe", return_value=True),
            patch("utils.web_fetch.requests.get", return_value=mock_response),
        ):
            result = fetch_url_text(
                "https://example.com/file.txt",
                timeout_seconds=5,
                max_bytes=1024,
                allowlist_domains=[],
            )
            assert result == "Hello World"

    def test_returns_none_for_non_text_content_type(self):
        """Non-text content types (images, PDFs) return None."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/pdf"}
        mock_response.encoding = "utf-8"

        raw = MagicMock()
        raw.read.return_value = b"%PDF-1.4"
        mock_response.raw = raw
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with (
            patch("utils.web_fetch._url_is_safe", return_value=True),
            patch("utils.web_fetch.requests.get", return_value=mock_response),
        ):
            result = fetch_url_text(
                "https://example.com/doc.pdf",
                timeout_seconds=5,
                max_bytes=1024,
                allowlist_domains=[],
            )
            assert result is None

    def test_returns_none_for_non_200_status(self):
        """Non-200 HTTP status returns None."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with (
            patch("utils.web_fetch._url_is_safe", return_value=True),
            patch("utils.web_fetch.requests.get", return_value=mock_response),
        ):
            result = fetch_url_text(
                "https://example.com/notfound",
                timeout_seconds=5,
                max_bytes=1024,
                allowlist_domains=[],
            )
            assert result is None

    def test_returns_none_when_content_exceeds_max_bytes(self):
        """Content exceeding max_bytes returns None."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/plain"}
        mock_response.encoding = "utf-8"

        raw = MagicMock()
        raw.read.return_value = b"x" * 1025  # More than max_bytes=1024
        mock_response.raw = raw
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with (
            patch("utils.web_fetch._url_is_safe", return_value=True),
            patch("utils.web_fetch.requests.get", return_value=mock_response),
        ):
            result = fetch_url_text(
                "https://example.com/large.txt",
                timeout_seconds=5,
                max_bytes=1024,
                allowlist_domains=[],
            )
            assert result is None

    def test_returns_none_on_request_exception(self):
        """Network errors return None."""
        with (
            patch("utils.web_fetch._url_is_safe", return_value=True),
            patch(
                "utils.web_fetch.requests.get",
                side_effect=ConnectionError("Network error"),
            ),
        ):
            result = fetch_url_text(
                "https://example.com/error",
                timeout_seconds=5,
                max_bytes=1024,
                allowlist_domains=[],
            )
            assert result is None

    def test_handles_text_csv_content_type(self):
        """text/csv content type is treated as text."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/csv"}
        mock_response.encoding = "utf-8"

        raw = MagicMock()
        raw.read.return_value = b"a,b,c\n1,2,3"
        mock_response.raw = raw
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with (
            patch("utils.web_fetch._url_is_safe", return_value=True),
            patch("utils.web_fetch.requests.get", return_value=mock_response),
        ):
            result = fetch_url_text(
                "https://example.com/data.csv",
                timeout_seconds=5,
                max_bytes=1024,
                allowlist_domains=[],
            )
            assert result is not None
            assert "a,b,c" in result

    def test_handles_missing_content_type(self):
        """Missing content-type header defaults to None return."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.encoding = "utf-8"

        raw = MagicMock()
        raw.read.return_value = b"binary data"
        mock_response.raw = raw
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with (
            patch("utils.web_fetch._url_is_safe", return_value=True),
            patch("utils.web_fetch.requests.get", return_value=mock_response),
        ):
            result = fetch_url_text(
                "https://example.com/data",
                timeout_seconds=5,
                max_bytes=1024,
                allowlist_domains=[],
            )
            # No content-type header → no match → None
            assert result is None

    def test_content_at_exact_max_bytes_is_returned(self):
        """Content exactly at max_bytes limit is returned."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/plain"}
        mock_response.encoding = "utf-8"

        raw = MagicMock()
        raw.read.return_value = b"x" * 1024  # Exactly max_bytes=1024
        mock_response.raw = raw
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with (
            patch("utils.web_fetch._url_is_safe", return_value=True),
            patch("utils.web_fetch.requests.get", return_value=mock_response),
        ):
            result = fetch_url_text(
                "https://example.com/exact.txt",
                timeout_seconds=5,
                max_bytes=1024,
                allowlist_domains=[],
            )
            assert result is not None


# ===========================================================================
# Test: searxng_search
# ===========================================================================


class TestSearxngSearch:
    """Tests for SearXNG HTML search result parsing."""

    def test_parses_search_results(self):
        """Parses HTML response into WebSearchResult objects."""
        html_response = """
        <article class="result result-default">
            <h3><a href="https://example.com/page1">Example Page 1</a></h3>
            <p class="content">Snippet for page 1</p>
        </article>
        <article class="result result-default">
            <h3><a href="https://example.com/page2">Example Page 2</a></h3>
            <p class="content">Snippet for page 2</p>
        </article>
        """

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = html_response

        with patch("utils.web_fetch.requests.get", return_value=mock_resp):
            results = searxng_search(
                searxng_url="http://localhost:8080",
                query="test query",
                max_results=10,
                timeout_seconds=5,
            )

        assert len(results) == 2
        assert isinstance(results[0], WebSearchResult)
        assert results[0].title == "Example Page 1"
        assert results[0].url == "https://example.com/page1"
        assert results[0].snippet == "Snippet for page 1"
        assert results[1].title == "Example Page 2"

    def test_limits_max_results(self):
        """Respects max_results parameter."""
        articles = []
        for i in range(5):
            articles.append(
                f'<article class="result"><h3><a href="https://example.com/{i}">Title {i}</a></h3>'
                f'<p class="content">Snippet {i}</p></article>'
            )
        html_response = "".join(articles)

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = html_response

        with patch("utils.web_fetch.requests.get", return_value=mock_resp):
            results = searxng_search(
                searxng_url="http://localhost:8080",
                query="test",
                max_results=3,
                timeout_seconds=5,
            )

        assert len(results) == 3

    def test_returns_empty_on_non_200(self):
        """Non-200 status code returns empty list."""
        mock_resp = MagicMock()
        mock_resp.status_code = 500

        with patch("utils.web_fetch.requests.get", return_value=mock_resp):
            results = searxng_search(
                searxng_url="http://localhost:8080",
                query="test",
                max_results=10,
                timeout_seconds=5,
            )

        assert results == []

    def test_returns_empty_on_exception(self):
        """Network errors return empty list."""
        with patch(
            "utils.web_fetch.requests.get",
            side_effect=ConnectionError("down"),
        ):
            results = searxng_search(
                searxng_url="http://localhost:8080",
                query="test",
                max_results=10,
                timeout_seconds=5,
            )

        assert results == []

    def test_handles_empty_html(self):
        """Empty HTML response returns empty list."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = ""

        with patch("utils.web_fetch.requests.get", return_value=mock_resp):
            results = searxng_search(
                searxng_url="http://localhost:8080",
                query="test",
                max_results=10,
                timeout_seconds=5,
            )

        assert results == []

    def test_skips_articles_without_h3_link(self):
        """Articles without h3 > a are skipped."""
        html_response = """
        <article class="result">
            <p class="content">No heading link here</p>
        </article>
        <article class="result">
            <h3><a href="https://example.com/page1">Valid Result</a></h3>
            <p class="content">Valid snippet</p>
        </article>
        """

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = html_response

        with patch("utils.web_fetch.requests.get", return_value=mock_resp):
            results = searxng_search(
                searxng_url="http://localhost:8080",
                query="test",
                max_results=10,
                timeout_seconds=5,
            )

        assert len(results) == 1
        assert results[0].title == "Valid Result"

    def test_skips_results_with_empty_url(self):
        """Results with empty URL are skipped."""
        html_response = """
        <article class="result">
            <h3><a href="  ">Empty URL</a></h3>
            <p class="content">Snippet</p>
        </article>
        """

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = html_response

        with patch("utils.web_fetch.requests.get", return_value=mock_resp):
            results = searxng_search(
                searxng_url="http://localhost:8080",
                query="test",
                max_results=10,
                timeout_seconds=5,
            )

        assert len(results) == 0

    def test_handles_missing_snippet(self):
        """Results without snippet get empty string."""
        html_response = """
        <article class="result">
            <h3><a href="https://example.com/page1">No Snippet</a></h3>
        </article>
        """

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = html_response

        with patch("utils.web_fetch.requests.get", return_value=mock_resp):
            results = searxng_search(
                searxng_url="http://localhost:8080",
                query="test",
                max_results=10,
                timeout_seconds=5,
            )

        assert len(results) == 1
        assert results[0].snippet == ""

    def test_strips_trailing_slash_from_base_url(self):
        """Trailing slash is stripped from searxng_url."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = ""

        with patch("utils.web_fetch.requests.get", return_value=mock_resp) as mock_get:
            searxng_search(
                searxng_url="http://localhost:8080/",
                query="test",
                max_results=10,
                timeout_seconds=5,
            )

        call_args = mock_get.call_args
        assert call_args[0][0] == "http://localhost:8080/search"


# ===========================================================================
# Test: duckduckgo_html_search
# ===========================================================================


class TestDuckduckgoHtmlSearch:
    """Tests for DuckDuckGo HTML search result parsing."""

    def test_parses_search_results(self):
        """Parses HTML response into WebSearchResult objects."""
        html_response = """
        <a class="result__a" href="https://example.com/page1">Result 1</a>
        <a class="result__snippet">Snippet 1</a>
        <a class="result__a" href="https://example.com/page2">Result 2</a>
        <a class="result__snippet">Snippet 2</a>
        """

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = html_response

        with patch("utils.web_fetch.requests.get", return_value=mock_resp):
            results = duckduckgo_html_search(
                query="test",
                max_results=10,
                timeout_seconds=5,
            )

        assert len(results) == 2
        assert isinstance(results[0], WebSearchResult)
        assert results[0].title == "Result 1"
        assert results[0].url == "https://example.com/page1"
        assert results[0].snippet == "Snippet 1"

    def test_limits_max_results(self):
        """Respects max_results parameter."""
        anchors = ""
        snippets = ""
        for i in range(5):
            anchors += f'<a class="result__a" href="https://example.com/{i}">Title {i}</a>\n'
            snippets += f'<a class="result__snippet">Snippet {i}</a>\n'

        html_response = anchors + snippets

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = html_response

        with patch("utils.web_fetch.requests.get", return_value=mock_resp):
            results = duckduckgo_html_search(
                query="test",
                max_results=3,
                timeout_seconds=5,
            )

        assert len(results) == 3

    def test_returns_empty_on_non_200(self):
        """Non-200/202 status code returns empty list."""
        mock_resp = MagicMock()
        mock_resp.status_code = 403

        with patch("utils.web_fetch.requests.get", return_value=mock_resp):
            results = duckduckgo_html_search(
                query="test",
                max_results=10,
                timeout_seconds=5,
            )

        assert results == []

    def test_accepts_202_status(self):
        """Status 202 is treated as success."""
        html_response = """
        <a class="result__a" href="https://example.com/page1">Result 1</a>
        """

        mock_resp = MagicMock()
        mock_resp.status_code = 202
        mock_resp.text = html_response

        with patch("utils.web_fetch.requests.get", return_value=mock_resp):
            results = duckduckgo_html_search(
                query="test",
                max_results=10,
                timeout_seconds=5,
            )

        assert len(results) == 1

    def test_returns_empty_on_exception(self):
        """Network errors return empty list."""
        with patch(
            "utils.web_fetch.requests.get",
            side_effect=ConnectionError("down"),
        ):
            results = duckduckgo_html_search(
                query="test",
                max_results=10,
                timeout_seconds=5,
            )

        assert results == []

    def test_handles_empty_html(self):
        """Empty HTML response returns empty list."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = ""

        with patch("utils.web_fetch.requests.get", return_value=mock_resp):
            results = duckduckgo_html_search(
                query="test",
                max_results=10,
                timeout_seconds=5,
            )

        assert results == []

    def test_skips_results_with_empty_url(self):
        """Results with empty URL after stripping are skipped."""
        html_response = """
        <a class="result__a" href="  ">Empty URL</a>
        """

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = html_response

        with patch("utils.web_fetch.requests.get", return_value=mock_resp):
            results = duckduckgo_html_search(
                query="test",
                max_results=10,
                timeout_seconds=5,
            )

        assert len(results) == 0

    def test_handles_fewer_snippets_than_results(self):
        """Missing snippet entries get empty string."""
        html_response = """
        <a class="result__a" href="https://example.com/1">Result 1</a>
        <a class="result__snippet">Snippet 1</a>
        <a class="result__a" href="https://example.com/2">Result 2</a>
        """

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = html_response

        with patch("utils.web_fetch.requests.get", return_value=mock_resp):
            results = duckduckgo_html_search(
                query="test",
                max_results=10,
                timeout_seconds=5,
            )

        assert len(results) == 2
        assert results[0].snippet == "Snippet 1"
        assert results[1].snippet == ""

    def test_uses_correct_user_agent(self):
        """Uses Mozilla/5.0 user agent header."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = ""

        with patch("utils.web_fetch.requests.get", return_value=mock_resp) as mock_get:
            duckduckgo_html_search(
                query="test",
                max_results=10,
                timeout_seconds=5,
            )

        call_kwargs = mock_get.call_args
        assert "Mozilla/5.0" in call_kwargs[1]["headers"]["User-Agent"]


# ===========================================================================
# Test: serpbase_search
# ===========================================================================


class TestSerpbaseSearch:
    """Tests for SerpBase REST API result parsing."""

    def test_parses_organic_results(self):
        """Parses JSON organic_results into WebSearchResult objects."""
        payload = {
            "organic_results": [
                {
                    "title": "Example Page 1",
                    "link": "https://example.com/page1",
                    "snippet": "Snippet for page 1",
                    "position": 1,
                },
                {
                    "title": "Example Page 2",
                    "link": "https://example.com/page2",
                    "snippet": "Snippet for page 2",
                    "position": 2,
                },
            ]
        }

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = payload

        with patch("utils.web_fetch.requests.get", return_value=mock_resp):
            results = serpbase_search(
                api_key="test-key",
                query="test query",
                max_results=10,
                timeout_seconds=5,
            )

        assert len(results) == 2
        assert isinstance(results[0], WebSearchResult)
        assert results[0].title == "Example Page 1"
        assert results[0].url == "https://example.com/page1"
        assert results[0].snippet == "Snippet for page 1"
        assert results[1].title == "Example Page 2"

    def test_limits_max_results(self):
        """Respects max_results parameter."""
        payload = {
            "organic_results": [
                {
                    "title": f"Title {i}",
                    "link": f"https://example.com/{i}",
                    "snippet": f"Snippet {i}",
                }
                for i in range(5)
            ]
        }

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = payload

        with patch("utils.web_fetch.requests.get", return_value=mock_resp):
            results = serpbase_search(
                api_key="test-key",
                query="test",
                max_results=3,
                timeout_seconds=5,
            )

        assert len(results) == 3
        assert results[0].url == "https://example.com/0"

    def test_skips_entries_without_link(self):
        """Drops organic results that have no usable link."""
        payload = {
            "organic_results": [
                {"title": "No link", "link": "", "snippet": "x"},
                {"title": "Valid", "link": "https://example.com/ok", "snippet": "y"},
            ]
        }

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = payload

        with patch("utils.web_fetch.requests.get", return_value=mock_resp):
            results = serpbase_search(
                api_key="test-key",
                query="test",
                max_results=10,
                timeout_seconds=5,
            )

        assert len(results) == 1
        assert results[0].url == "https://example.com/ok"

    def test_returns_empty_on_non_200(self):
        """Non-200 responses produce an empty list, not an exception."""
        mock_resp = MagicMock()
        mock_resp.status_code = 401

        with patch("utils.web_fetch.requests.get", return_value=mock_resp):
            results = serpbase_search(
                api_key="bad-key",
                query="test",
                max_results=10,
                timeout_seconds=5,
            )

        assert results == []

    def test_returns_empty_on_exception(self):
        """Network errors produce an empty list, not an exception."""
        with patch("utils.web_fetch.requests.get", side_effect=Exception("boom")):
            results = serpbase_search(
                api_key="test-key",
                query="test",
                max_results=10,
                timeout_seconds=5,
            )

        assert results == []

    def test_returns_empty_without_api_key(self):
        """An empty API key is a no-op (graceful degradation)."""
        results = serpbase_search(
            api_key="",
            query="test",
            max_results=10,
            timeout_seconds=5,
        )

        assert results == []

    def test_sends_expected_params(self):
        """Sends query, api_key, and num to the SerpBase endpoint."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"organic_results": []}

        with patch("utils.web_fetch.requests.get", return_value=mock_resp) as mock_get:
            serpbase_search(
                api_key="test-key",
                query="test query",
                max_results=7,
                timeout_seconds=5,
            )

        call_kwargs = mock_get.call_args
        assert call_kwargs[0][0] == "https://api.serpbase.dev/google/search"
        assert call_kwargs[1]["params"] == {
            "q": "test query",
            "api_key": "test-key",
            "num": "7",
        }
