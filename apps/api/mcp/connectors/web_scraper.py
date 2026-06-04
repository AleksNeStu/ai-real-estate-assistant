"""
Web Scraper MCP Connector.

This module provides a configurable web scraping connector that demonstrates
the MCP connector implementation pattern. It supports CSS selector-based
content extraction with rate limiting and retry logic.

Task #72: MCP Web Scraper Connector
"""

import asyncio
import fnmatch
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from core.security_utils import sanitize_for_log
from mcp.base import MCPConnector
from mcp.config import MCPConnectorConfig, MCPEdition
from mcp.exceptions import (
    MCPConnectionError,
    MCPOperationError,
    MCPTimeoutError,
)
from mcp.rate_limiter import get_connector_rate_limiter
from mcp.result import MCPConnectorResult

logger = logging.getLogger(__name__)


@dataclass
class ScraperTarget:
    """
    Configuration for a scraping target.

    Attributes:
        url_pattern: URL glob pattern (e.g., "https://example.com/*")
        selectors: CSS selectors mapping field_name -> CSS selector
        max_depth: Maximum link following depth (default: 1, no following)
        enabled: Whether this target is active
    """

    url_pattern: str
    selectors: Dict[str, str] = field(default_factory=dict)
    max_depth: int = 1
    enabled: bool = True

    def matches(self, url: str) -> bool:
        """Check if URL matches this target's pattern."""
        return fnmatch.fnmatch(url, self.url_pattern)


@dataclass
class WebScraperConfig:
    """
    Extended configuration for WebScraperConnector.

    Attributes:
        allowed_domains: List of domains that can be scraped
        targets: Pre-configured scraping targets
        rate_limit_rpm: Requests per minute limit
        max_retries: Maximum retry attempts for failed requests
        retry_delay_seconds: Base delay between retries (exponential backoff)
        cache_ttl_seconds: Response cache TTL (0 = disabled)
        user_agent: User-Agent header for requests
        respect_robots_txt: Whether to check robots.txt (not implemented yet)
        timeout_seconds: Request timeout
    """

    allowed_domains: List[str] = field(default_factory=list)
    targets: List[ScraperTarget] = field(default_factory=list)
    rate_limit_rpm: int = 30
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    cache_ttl_seconds: int = 300
    user_agent: str = "MCP-WebScraper/1.0"
    respect_robots_txt: bool = True
    timeout_seconds: float = 30.0


class WebScraperConnector(MCPConnector[Dict[str, Any]]):
    """
    MCP connector for web scraping with configurable targets.

    This connector provides safe, configurable web scraping capabilities
    with the following features:

    - Domain allowlist for security
    - CSS selector-based content extraction
    - Rate limiting with exponential backoff retry
    - Response caching (optional)
    - Comprehensive error handling

    Operations:
        - scrape: Extract content from a single URL
        - scrape_batch: Extract content from multiple URLs
        - validate_selector: Test CSS selector syntax
        - list_targets: List configured targets
        - health_check: Check connector health

    Attributes:
        name: "web_scraper"
        display_name: "Web Scraper"
        description: "Configurable web scraping connector"
        requires_api_key: False
        allowlisted: True (CE available)
        min_edition: MCPEdition.COMMUNITY
        supports_streaming: False

    Example:
        async with WebScraperConnector() as scraper:
            result = await scraper.execute("scrape", {
                "url": "https://example.com/article",
                "selectors": {"title": "h1", "content": "article"}
            })
            if result.success:
                print(result.data)
    """

    name = "web_scraper"
    display_name = "Web Scraper"
    description = "Configurable web scraping connector for content extraction"
    requires_api_key = False
    allowlisted = True  # Available in Community Edition
    min_edition = MCPEdition.COMMUNITY
    supports_streaming = False
    default_timeout = 30.0

    def __init__(
        self,
        config: Optional[MCPConnectorConfig] = None,
        scraper_config: Optional[WebScraperConfig] = None,
    ) -> None:
        """
        Initialize the Web Scraper connector.

        Args:
            config: Base MCP connector configuration
            scraper_config: Web scraper specific configuration

        Raises:
            MCPConfigError: If configuration is invalid
        """
        super().__init__(config)
        self._scraper_config = scraper_config or WebScraperConfig()
        self._client: Optional[httpx.AsyncClient] = None
        self._cache: Dict[str, tuple[float, Dict[str, Any]]] = {}
        self._request_count = 0
        self._error_count = 0

        # Configure rate limiter
        rate_limiter = get_connector_rate_limiter()
        rate_limiter.configure_connector(
            self.name,
            requests_per_minute=self._scraper_config.rate_limit_rpm,
            burst_size=5,
            enabled=True,
        )

    async def connect(self) -> bool:
        """
        Initialize the HTTP client.

        Returns:
            True if connection successful

        Raises:
            MCPConnectionError: If client initialization fails
        """
        if self._connected:
            return True

        try:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self._scraper_config.timeout_seconds),
                headers={
                    "User-Agent": self._scraper_config.user_agent,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                },
                follow_redirects=True,
                max_redirects=5,
            )
            self._connected = True
            logger.info(
                "WebScraperConnector connected with %s allowed domains",
                len(self._scraper_config.allowed_domains),
            )
            return True
        except Exception as e:
            logger.error("Failed to initialize HTTP client: %s", sanitize_for_log(e))
            raise MCPConnectionError(
                f"Failed to initialize HTTP client: {e}",
                connector_name=self.name,
            ) from None

    async def disconnect(self) -> None:
        """Close the HTTP client and clear cache."""
        if self._client:
            await self._client.aclose()
            self._client = None
        self._cache.clear()
        self._connected = False
        logger.info("WebScraperConnector disconnected")

    async def health_check(self) -> MCPConnectorResult[Dict[str, Any]]:
        """
        Check health status of the connector.

        Returns:
            MCPConnectorResult with health information
        """
        return MCPConnectorResult.success_result(
            data={
                "healthy": self._connected,
                "connected": self._connected,
                "allowed_domains": len(self._scraper_config.allowed_domains),
                "configured_targets": len(self._scraper_config.targets),
                "request_count": self._request_count,
                "error_count": self._error_count,
                "cache_size": len(self._cache),
                "rate_limit_rpm": self._scraper_config.rate_limit_rpm,
            },
            connector_name=self.name,
            operation="health_check",
        )

    async def execute(
        self,
        operation: str,
        params: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> MCPConnectorResult[Dict[str, Any]]:
        """
        Execute a web scraping operation.

        Args:
            operation: Operation name (scrape, scrape_batch, validate_selector, list_targets)
            params: Operation parameters
            **kwargs: Additional options

        Returns:
            MCPConnectorResult with operation result
        """
        params = params or {}

        # Check rate limit
        rate_limiter = get_connector_rate_limiter()
        allowed, rate_headers = await rate_limiter.check_rate_limit(self.name)

        if not allowed:
            return MCPConnectorResult.error_result(
                errors=["Rate limit exceeded. Please retry later."],
                connector_name=self.name,
                operation=operation,
                metadata={"rate_limit_headers": rate_headers},
            )

        # Route to operation handler
        try:
            if operation == "scrape":
                return await self._scrape(params)
            elif operation == "scrape_batch":
                return await self._scrape_batch(params)
            elif operation == "validate_selector":
                return self._validate_selector(params)
            elif operation == "list_targets":
                return self._list_targets()
            else:
                return MCPConnectorResult.error_result(
                    errors=[f"Unknown operation: {operation}"],
                    connector_name=self.name,
                    operation=operation,
                )
        except MCPTimeoutError as e:
            self._error_count += 1
            return MCPConnectorResult.error_result(
                errors=[str(e)],
                connector_name=self.name,
                operation=operation,
                metadata={"error_type": "timeout"},
            )
        except MCPOperationError as e:
            self._error_count += 1
            return MCPConnectorResult.error_result(
                errors=[str(e)],
                connector_name=self.name,
                operation=operation,
                metadata={"error_type": "operation_error"},
            )
        except Exception as e:
            self._error_count += 1
            logger.exception("Unexpected error in %s", sanitize_for_log(operation))
            return MCPConnectorResult.error_result(
                errors=[f"Internal error: {e}"],
                connector_name=self.name,
                operation=operation,
                metadata={"error_type": "internal"},
            )

    async def _scrape(self, params: Dict[str, Any]) -> MCPConnectorResult[Dict[str, Any]]:
        """
        Scrape a single URL.

        Args:
            params: Must contain 'url', optionally 'selectors' and 'timeout'

        Returns:
            MCPConnectorResult with scraped content
        """
        url = params.get("url")
        if not url:
            return MCPConnectorResult.error_result(
                errors=["Missing required parameter: url"],
                connector_name=self.name,
                operation="scrape",
            )

        # Validate URL and domain
        domain = self._validate_url(url)

        # Get selectors
        selectors = params.get("selectors", {})

        # Find matching target config if any
        target_config = self._find_target_config(url)
        if target_config and not selectors:
            selectors = target_config.selectors

        if not selectors:
            selectors = {"content": "body"}  # Default: extract all body text

        # Check cache
        cache_key = f"{url}:{hash(frozenset(selectors.items()))}"
        if self._scraper_config.cache_ttl_seconds > 0:
            cached = self._cache.get(cache_key)
            if cached and time.time() - cached[0] < self._scraper_config.cache_ttl_seconds:
                self._request_count += 1
                return MCPConnectorResult.success_result(
                    data=cached[1],
                    connector_name=self.name,
                    operation="scrape",
                    metadata={"url": url, "cached": True, "domain": domain},
                )

        # Execute request with retry
        html = await self._fetch_with_retry(url, params.get("timeout"))

        # Parse content
        result_data = self._parse_content(html, selectors)
        result_data["url"] = url
        result_data["domain"] = domain
        result_data["scraped_at"] = time.time()

        # Cache result
        if self._scraper_config.cache_ttl_seconds > 0:
            self._cache[cache_key] = (time.time(), result_data)

        self._request_count += 1

        return MCPConnectorResult.success_result(
            data=result_data,
            connector_name=self.name,
            operation="scrape",
            metadata={"url": url, "cached": False, "domain": domain},
        )

    async def _scrape_batch(self, params: Dict[str, Any]) -> MCPConnectorResult[Dict[str, Any]]:
        """
        Scrape multiple URLs with concurrency limit.

        Args:
            params: Must contain 'urls', optionally 'selectors', 'concurrency'

        Returns:
            MCPConnectorResult with batch results
        """
        urls = params.get("urls", [])
        if not urls:
            return MCPConnectorResult.error_result(
                errors=["Missing required parameter: urls"],
                connector_name=self.name,
                operation="scrape_batch",
            )

        if len(urls) > 50:
            return MCPConnectorResult.error_result(
                errors=["Maximum 50 URLs per batch"],
                connector_name=self.name,
                operation="scrape_batch",
            )

        selectors = params.get("selectors", {"content": "body"})
        concurrency = min(params.get("concurrency", 5), 10)  # Max 10 concurrent

        results = []
        semaphore = asyncio.Semaphore(concurrency)

        async def scrape_one(url: str) -> Dict[str, Any]:
            async with semaphore:
                result = await self._scrape(
                    {
                        "url": url,
                        "selectors": selectors,
                    }
                )
                return {
                    "url": url,
                    "success": result.success,
                    "data": result.data if result.success else None,
                    "errors": result.errors if not result.success else None,
                }

        # Execute all requests
        tasks = [scrape_one(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        successful = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
        failed = len(urls) - successful

        return MCPConnectorResult.success_result(
            data={
                "results": results,
                "total": len(urls),
                "successful": successful,
                "failed": failed,
            },
            connector_name=self.name,
            operation="scrape_batch",
            metadata={"urls_count": len(urls), "concurrency": concurrency},
        )

    def _validate_selector(self, params: Dict[str, Any]) -> MCPConnectorResult[Dict[str, Any]]:
        """
        Validate CSS selector syntax.

        Args:
            params: Must contain 'selector', optionally 'sample_html'

        Returns:
            MCPConnectorResult with validation result
        """
        selector = params.get("selector")
        if not selector:
            return MCPConnectorResult.error_result(
                errors=["Missing required parameter: selector"],
                connector_name=self.name,
                operation="validate_selector",
            )

        try:
            # Try to parse selector with BeautifulSoup
            sample_html = params.get("sample_html", "<html><body><div>test</div></body></html>")
            soup = BeautifulSoup(sample_html, "lxml")
            elements = soup.select(selector)

            return MCPConnectorResult.success_result(
                data={
                    "selector": selector,
                    "valid": True,
                    "matched_elements": len(elements),
                },
                connector_name=self.name,
                operation="validate_selector",
            )
        except Exception as e:
            return MCPConnectorResult.success_result(
                data={
                    "selector": selector,
                    "valid": False,
                    "error": str(e),
                },
                connector_name=self.name,
                operation="validate_selector",
            )

    def _list_targets(self) -> MCPConnectorResult[Dict[str, Any]]:
        """
        List configured scraping targets.

        Returns:
            MCPConnectorResult with target list
        """
        targets = [
            {
                "url_pattern": t.url_pattern,
                "selectors": t.selectors,
                "max_depth": t.max_depth,
                "enabled": t.enabled,
            }
            for t in self._scraper_config.targets
        ]

        return MCPConnectorResult.success_result(
            data={
                "targets": targets,
                "allowed_domains": self._scraper_config.allowed_domains,
            },
            connector_name=self.name,
            operation="list_targets",
        )

    def _validate_url(self, url: str) -> str:
        """
        Validate URL format and domain allowlist.

        Args:
            url: URL to validate

        Returns:
            Domain of the URL

        Raises:
            MCPOperationError: If URL is invalid or domain not allowed
        """
        try:
            parsed = urlparse(url)
            if parsed.scheme not in ("http", "https"):
                raise MCPOperationError(
                    f"Invalid URL scheme: {parsed.scheme}. Only http and https are allowed.",
                    connector_name=self.name,
                )

            domain = parsed.netloc.lower()
            if not domain:
                raise MCPOperationError(
                    "Invalid URL: missing domain",
                    connector_name=self.name,
                )

            # Check domain allowlist
            if self._scraper_config.allowed_domains:
                if not self._is_domain_allowed(domain):
                    raise MCPOperationError(
                        f"Domain '{domain}' is not in the allowed list",
                        connector_name=self.name,
                    )

            return domain

        except MCPOperationError:
            raise
        except Exception as e:
            raise MCPOperationError(
                f"Invalid URL: {e}",
                connector_name=self.name,
            ) from None

    def _is_domain_allowed(self, domain: str) -> bool:
        """Check if domain matches allowed list."""
        for allowed in self._scraper_config.allowed_domains:
            # Support wildcard patterns
            if fnmatch.fnmatch(domain, allowed):
                return True
            # Support subdomain matching
            if domain.endswith(f".{allowed}"):
                return True
            if allowed == domain:
                return True
        return False

    def _find_target_config(self, url: str) -> Optional[ScraperTarget]:
        """Find matching target configuration for URL."""
        for target in self._scraper_config.targets:
            if target.enabled and target.matches(url):
                return target
        return None

    async def _fetch_with_retry(self, url: str, timeout: Optional[float] = None) -> str:
        """
        Fetch URL content with exponential backoff retry.

        Args:
            url: URL to fetch
            timeout: Optional timeout override

        Returns:
            HTML content as string

        Raises:
            MCPTimeoutError: If request times out after retries
            MCPOperationError: If request fails after retries
        """
        if not self._client:
            raise MCPConnectionError("Connector not connected", connector_name=self.name)

        max_retries = self._scraper_config.max_retries
        base_delay = self._scraper_config.retry_delay_seconds
        request_timeout = timeout or self._scraper_config.timeout_seconds

        last_error: Optional[Exception] = None

        for attempt in range(max_retries):
            try:
                response = await self._client.get(url, timeout=request_timeout)

                if response.status_code == 200:
                    return response.text
                elif response.status_code == 429:
                    # Rate limited - wait and retry
                    retry_after = float(
                        response.headers.get("Retry-After", base_delay * (2**attempt))
                    )
                    logger.warning(
                        "Rate limited by %s, waiting %ss",
                        sanitize_for_log(url),
                        sanitize_for_log(retry_after),
                    )
                    await asyncio.sleep(retry_after)
                elif response.status_code >= 500:
                    # Server error - retry with backoff
                    last_error = MCPOperationError(
                        f"Server error: HTTP {response.status_code}",
                        connector_name=self.name,
                    )
                    delay = base_delay * (2**attempt)
                    logger.warning(
                        "Server error from %s, retrying in %ss",
                        sanitize_for_log(url),
                        sanitize_for_log(delay),
                    )
                    await asyncio.sleep(delay)
                elif response.status_code == 403:
                    # Blocked - don't retry
                    raise MCPOperationError(
                        f"Access blocked (403): {url}",
                        connector_name=self.name,
                    )
                elif response.status_code == 404:
                    # Not found - don't retry
                    raise MCPOperationError(
                        f"Page not found (404): {url}",
                        connector_name=self.name,
                    )
                else:
                    # Other client errors - don't retry
                    raise MCPOperationError(
                        f"HTTP error {response.status_code}: {url}",
                        connector_name=self.name,
                    )

            except httpx.TimeoutException:
                last_error = MCPTimeoutError(
                    f"Request timed out: {url}",
                    connector_name=self.name,
                )
                if attempt < max_retries - 1:
                    delay = base_delay * (2**attempt)
                    logger.warning(
                        "Timeout for %s, retrying in %ss",
                        sanitize_for_log(url),
                        sanitize_for_log(delay),
                    )
                    await asyncio.sleep(delay)
            except httpx.NetworkError as e:
                last_error = MCPConnectionError(
                    f"Network error: {e}",
                    connector_name=self.name,
                )
                if attempt < max_retries - 1:
                    delay = base_delay * (2**attempt)
                    logger.warning(
                        "Network error for %s, retrying in %ss",
                        sanitize_for_log(url),
                        sanitize_for_log(delay),
                    )
                    await asyncio.sleep(delay)

        # All retries exhausted
        if last_error:
            raise last_error
        raise MCPOperationError(
            f"Max retries exceeded: {url}",
            connector_name=self.name,
        )

    def _parse_content(self, html: str, selectors: Dict[str, str]) -> Dict[str, Any]:
        """
        Parse HTML content using CSS selectors.

        Args:
            html: HTML content to parse
            selectors: CSS selectors mapping

        Returns:
            Dictionary with extracted content
        """
        soup = BeautifulSoup(html, "lxml")
        result: dict[str, str | list[str] | None] = {}

        for field_name, selector in selectors.items():
            try:
                elements = soup.select(selector)

                if len(elements) == 0:
                    result[field_name] = None
                elif len(elements) == 1:
                    result[field_name] = self._clean_text(elements[0].get_text())
                else:
                    result[field_name] = [self._clean_text(el.get_text()) for el in elements]

            except Exception as e:
                logger.warning(
                    "Failed to parse selector '%s': %s",
                    sanitize_for_log(selector),
                    sanitize_for_log(e),
                )
                result[field_name] = None

        return result

    def _clean_text(self, text: str) -> str:
        """
        Clean and normalize extracted text.

        Args:
            text: Raw text to clean

        Returns:
            Cleaned text
        """
        if not text:
            return ""
        # Remove excess whitespace
        text = re.sub(r"\s+", " ", text)
        return text.strip()
