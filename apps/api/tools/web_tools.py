import json
import os
from typing import Any, Optional

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field, PrivateAttr

from utils.web_fetch import (
    duckduckgo_html_search,
    fetch_url_text,
    searxng_search,
    serpbase_search,
)


class WebSearchInput(BaseModel):
    query: str = Field(description="Search query string")
    max_results: int = Field(default=5, description="Max number of results to return")


class WebSearchTool(BaseTool):
    name: str = "web_search"
    description: str = (
        "Search the web for relevant pages. "
        "Returns JSON: {query, provider, results:[{id,title,url,snippet}]}."
    )

    _searxng_url: Optional[str] = PrivateAttr()
    _serpbase_api_key: Optional[str] = PrivateAttr()
    _timeout_seconds: float = PrivateAttr()

    def __init__(self, searxng_url: Optional[str], timeout_seconds: float, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._searxng_url = searxng_url.strip() if searxng_url else None
        self._serpbase_api_key = os.environ.get("SERPBASE_API_KEY", "").strip() or None
        self._timeout_seconds = float(timeout_seconds)

    def _run(self, query: str, max_results: int = 5) -> str:
        provider = "searxng"
        results = []
        if self._searxng_url:
            results = searxng_search(
                searxng_url=self._searxng_url,
                query=query,
                max_results=int(max_results),
                timeout_seconds=self._timeout_seconds,
            )
        if not results and self._serpbase_api_key:
            provider = "serpbase"
            results = serpbase_search(
                api_key=self._serpbase_api_key,
                query=query,
                max_results=int(max_results),
                timeout_seconds=self._timeout_seconds,
            )
        if not results:
            provider = "duckduckgo"
            results = duckduckgo_html_search(
                query=query,
                max_results=int(max_results),
                timeout_seconds=self._timeout_seconds,
            )

        payload = {
            "query": query,
            "provider": provider,
            "results": [
                {"id": idx + 1, "title": r.title, "url": r.url, "snippet": r.snippet}
                for idx, r in enumerate(results[: max(0, int(max_results))])
            ],
        }
        return json.dumps(payload, ensure_ascii=False)

    async def _arun(self, *args: Any, **kwargs: Any) -> str:
        return self._run(*args, **kwargs)


class OpenUrlInput(BaseModel):
    url: str = Field(description="URL to open")


class OpenUrlTool(BaseTool):
    name: str = "open_url"
    description: str = (
        "Fetch and extract text from a URL (SSRF-safe, size-limited). "
        "Returns JSON: {url, ok, text}."
    )

    _timeout_seconds: float = PrivateAttr()
    _max_bytes: int = PrivateAttr()
    _allowlist_domains: list[str] = PrivateAttr()
    _max_text_chars: int = PrivateAttr()

    def __init__(
        self,
        *,
        timeout_seconds: float,
        max_bytes: int,
        allowlist_domains: list[str],
        max_text_chars: int = 8000,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._timeout_seconds = float(timeout_seconds)
        self._max_bytes = int(max_bytes)
        self._allowlist_domains = list(allowlist_domains or [])
        self._max_text_chars = int(max_text_chars)

    def _run(self, url: str) -> str:
        text = fetch_url_text(
            url,
            timeout_seconds=self._timeout_seconds,
            max_bytes=self._max_bytes,
            allowlist_domains=self._allowlist_domains,
        )
        payload = {
            "url": url,
            "ok": bool(text),
            "text": (text or "")[: max(0, int(self._max_text_chars))],
        }
        return json.dumps(payload, ensure_ascii=False)

    async def _arun(self, *args: Any, **kwargs: Any) -> str:
        return self._run(*args, **kwargs)


def create_web_tools(
    *,
    searxng_url: Optional[str],
    web_fetch_timeout_seconds: float,
    web_fetch_max_bytes: int,
    web_allowlist_domains: list[str],
) -> list[BaseTool]:
    return [
        WebSearchTool(searxng_url=searxng_url, timeout_seconds=web_fetch_timeout_seconds),
        OpenUrlTool(
            timeout_seconds=web_fetch_timeout_seconds,
            max_bytes=web_fetch_max_bytes,
            allowlist_domains=web_allowlist_domains,
        ),
    ]
