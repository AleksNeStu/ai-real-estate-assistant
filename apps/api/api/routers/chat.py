import asyncio
import inspect
import json
import logging
import time
import uuid
from typing import Annotated, Any, Optional

import anyio
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from langchain_core.language_models import BaseChatModel

from agents.hybrid_agent import create_hybrid_agent
from ai.memory import (
    get_context_manager,
    get_optimized_memory,
    init_context_manager,
)
from api.chat_sources import serialize_chat_sources, serialize_web_sources
from api.dependencies import get_llm, get_vector_store
from api.models import ChatRequest, ChatResponse
from config.settings import get_settings
from core.circuit_breaker import ServiceDegradedError
from utils.free_tier import get_free_tier_rate_limiter, get_llm_for_free_user
from utils.sanitization import (
    sanitize_chat_message,
    sanitize_for_logging,
    sanitize_intermediate_steps,
)
from utils.streaming import (
    HeartbeatConfig,
    StreamMetrics,
    format_sse_event,
    format_sse_heartbeat,
    should_send_heartbeat,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Chat"])


async def _check_free_tier_rate_limit(req: Request) -> None:
    """Enforce free tier rate limits keyed by client IP."""
    client_ip = (
        req.headers.get("x-forwarded-for", req.client.host if req.client else "unknown")
        .split(",")[0]
        .strip()
    )

    limiter = get_free_tier_rate_limiter()
    allowed, reason, retry_after = await limiter.check(client_ip)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Free tier rate limit: {reason}. Retry after {retry_after}s.",
            headers={"Retry-After": str(retry_after)},
        )


def _build_agent_and_process(
    request: ChatRequest,
    req: Request,
    llm: BaseChatModel,
    store: Any,
) -> tuple[object, str, str]:
    """Common setup for chat endpoints. Returns (agent, sanitized_message, session_id)."""
    try:
        sanitized_message = sanitize_chat_message(request.message)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from None

    if not store:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chat is temporarily unavailable. The property database is offline. "
            "Please try again in a moment.",
        )

    settings = get_settings()
    session_id = request.session_id or str(uuid.uuid4())

    if not get_context_manager():
        init_context_manager(settings)

    model_id = getattr(llm, "model_name", getattr(llm, "model", "gpt-4o-mini"))

    memory, context_metrics = get_optimized_memory(
        session_id=session_id,
        model_id=model_id,
        llm=llm,
        max_utilization=settings.context_max_utilization_percent / 100.0,
    )

    if context_metrics and settings.context_metrics_enabled:
        logger.info(
            "Context optimization: session=%s tokens=%d/%d utilization=%.1f%% cost=$%.4f",
            sanitize_for_logging(session_id),
            context_metrics.input_tokens,
            context_metrics.context_window_limit,
            context_metrics.utilization_percent,
            context_metrics.estimated_cost_usd,
        )

    agent_kwargs = {
        "llm": llm,
        "retriever": store.get_retriever(),
        "memory": memory,
        "internet_enabled": bool(getattr(settings, "internet_enabled", False)),
        "searxng_url": getattr(settings, "searxng_url", None),
        "web_search_max_results": int(getattr(settings, "web_search_max_results", 5)),
        "web_fetch_timeout_seconds": float(getattr(settings, "web_fetch_timeout_seconds", 10)),
        "web_fetch_max_bytes": int(getattr(settings, "web_fetch_max_bytes", 300_000)),
        "web_allowlist_domains": list(getattr(settings, "web_allowlist_domains", []) or []),
    }
    sig = inspect.signature(create_hybrid_agent)
    if any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()):
        filtered_kwargs = agent_kwargs
    else:
        filtered_kwargs = {k: v for k, v in agent_kwargs.items() if k in sig.parameters}
    agent = create_hybrid_agent(**filtered_kwargs)

    return agent, sanitized_message, session_id


@router.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat_endpoint(
    request: ChatRequest,
    req: Request,
    llm: Annotated[BaseChatModel, Depends(get_llm)],
    store: Annotated[Optional[Any], Depends(get_vector_store)],
):
    """
    Process a chat message using the hybrid agent with session persistence.
    Requires API key authentication.
    """
    settings = get_settings()
    request_id = getattr(req.state, "request_id", None) or str(uuid.uuid4())

    try:
        agent, sanitized_message, session_id = _build_agent_and_process(request, req, llm, store)
        sources_max_items = max(0, int(settings.chat_sources_max_items))
        sources_max_content_chars = max(0, int(settings.chat_source_content_max_chars))
        sources_max_total_bytes = max(0, int(settings.chat_sources_max_total_bytes))

        if request.stream:
            analysis = getattr(getattr(agent, "analyzer", None), "analyze", None)
            analyzed = analysis(sanitized_message) if callable(analysis) else None
            requires_web = False
            if analyzed is not None:
                from agents.query_analyzer import QueryAnalysis

                if not isinstance(analyzed, QueryAnalysis):
                    analyzed = None
            if analyzed is not None:
                requires_web = bool(
                    getattr(analyzed, "requires_external_data", False)
                    or any(
                        getattr(t, "value", str(t)) == "web_search"
                        for t in getattr(analyzed, "tools_needed", []) or []
                    )
                )

            async def event_generator():
                # Initialize streaming configuration (Task #74)
                heartbeat_config = HeartbeatConfig(
                    interval_seconds=settings.stream_heartbeat_interval_seconds,
                    timeout_seconds=settings.stream_timeout_seconds,
                )
                stream_metrics = StreamMetrics(
                    session_id=session_id,
                    request_id=request_id,
                )
                last_heartbeat = time.time()

                sources_payload: dict[str, object] = {
                    "sources": [],
                    "sources_truncated": False,
                    "session_id": session_id,
                    "request_id": request_id,
                }

                try:
                    # Add timeout protection for streaming
                    with anyio.fail_after(settings.stream_timeout_seconds):
                        if requires_web:
                            result = await asyncio.to_thread(agent.process_query, sanitized_message)
                            raw_answer = result.get("answer", "")
                            answer_text = (
                                raw_answer if isinstance(raw_answer, str) else str(raw_answer)
                            )
                            if answer_text:
                                # Record metrics for web path
                                chunk_bytes = len(answer_text.encode("utf-8"))
                                stream_metrics.record_chunk(chunk_bytes)
                                yield f"data: {json.dumps({'content': answer_text}, ensure_ascii=False, default=str)}\n\n"

                            raw_sources = (
                                result.get("sources")
                                if isinstance(result.get("sources"), list)
                                else []
                            )
                            if (
                                raw_sources
                                and isinstance(raw_sources, list)
                                and isinstance(raw_sources[0], dict)
                                and "content" in raw_sources[0]
                                and "metadata" in raw_sources[0]
                            ):
                                sources = raw_sources
                                sources_truncated = False
                            else:
                                sources, sources_truncated = serialize_web_sources(
                                    raw_sources or [],
                                    max_items=sources_max_items,
                                    max_content_chars=sources_max_content_chars,
                                    max_total_bytes=sources_max_total_bytes,
                                )
                            sources_payload["sources"] = sources
                            sources_payload["sources_truncated"] = sources_truncated

                            if request.include_intermediate_steps:
                                raw_steps = result.get("intermediate_steps") or []
                                # Sanitize steps to redact sensitive data (API keys, tokens, passwords)
                                safe_steps = sanitize_intermediate_steps(raw_steps)
                                sources_payload["intermediate_steps"] = safe_steps
                        else:
                            async for chunk in agent.astream_query(sanitized_message):
                                # Check if heartbeat needed (Task #74)
                                if should_send_heartbeat(last_heartbeat, heartbeat_config):
                                    yield format_sse_heartbeat()
                                    last_heartbeat = time.time()

                                # Record chunk metrics
                                chunk_bytes = (
                                    len(chunk.encode("utf-8"))
                                    if isinstance(chunk, str)
                                    else len(chunk)
                                )
                                stream_metrics.record_chunk(chunk_bytes)
                                yield f"data: {chunk}\n\n"

                            if hasattr(agent, "get_sources_for_query"):
                                try:
                                    docs = agent.get_sources_for_query(sanitized_message)
                                    sources, sources_truncated = serialize_chat_sources(
                                        docs,
                                        max_items=sources_max_items,
                                        max_content_chars=sources_max_content_chars,
                                        max_total_bytes=sources_max_total_bytes,
                                    )
                                    sources_payload["sources"] = sources
                                    sources_payload["sources_truncated"] = sources_truncated
                                except Exception:
                                    sources_payload["sources"] = []
                                    sources_payload["sources_truncated"] = False

                        # Mark stream as completed and send metrics (Task #74)
                        stream_metrics.complete()

                        # Send meta event with sources
                        yield "event: meta\n"
                        yield f"data: {json.dumps(sources_payload)}\n\n"

                        # Send metrics event if enabled (Task #74)
                        if settings.stream_metrics_enabled:
                            yield format_sse_event("metrics", json.dumps(stream_metrics.to_dict()))

                        yield "data: [DONE]\n\n"
                except TimeoutError:
                    # Send timeout error event
                    stream_metrics.record_error()
                    error_payload = {"error": "Stream timeout exceeded", "request_id": request_id}
                    yield "event: error\n"
                    yield f"data: {json.dumps(error_payload)}\n\n"
                    yield "data: [DONE]\n\n"
                except Exception as e:
                    # Log error and send error event for client recovery
                    stream_metrics.record_error()
                    logger.error(f"Stream error (request_id={request_id}): {e}")
                    error_payload = {"error": str(e), "request_id": request_id}
                    yield "event: error\n"
                    yield f"data: {json.dumps(error_payload)}\n\n"
                    yield "data: [DONE]\n\n"
                finally:
                    # Always ensure stream terminates
                    pass

            # Return streaming response with heartbeat headers (Task #74)
            return StreamingResponse(
                event_generator(),
                media_type="text/event-stream",
                headers={
                    "X-Heartbeat-Interval": str(settings.stream_heartbeat_interval_seconds),
                    "X-Stream-Timeout": str(settings.stream_timeout_seconds),
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",  # Disable nginx buffering
                    "X-AI-Generated": "true",  # EU AI Act compliance disclosure
                },
            )

        result = await asyncio.to_thread(agent.process_query, sanitized_message)

        answer = result.get("answer", "")
        if "sources" in result and isinstance(result.get("sources"), list):
            raw_sources = result.get("sources") or []
            if (
                raw_sources
                and isinstance(raw_sources, list)
                and isinstance(raw_sources[0], dict)
                and "content" in raw_sources[0]
                and "metadata" in raw_sources[0]
            ):
                sources = raw_sources
                sources_truncated = False
            else:
                sources, sources_truncated = serialize_web_sources(
                    raw_sources,
                    max_items=sources_max_items,
                    max_content_chars=sources_max_content_chars,
                    max_total_bytes=sources_max_total_bytes,
                )
        else:
            sources, sources_truncated = serialize_chat_sources(
                result.get("source_documents") or [],
                max_items=sources_max_items,
                max_content_chars=sources_max_content_chars,
                max_total_bytes=sources_max_total_bytes,
            )

        # Sanitize intermediate steps if requested
        intermediate_steps = None
        if request.include_intermediate_steps:
            raw_steps = result.get("intermediate_steps") or []
            intermediate_steps = sanitize_intermediate_steps(raw_steps) if raw_steps else None

        # Build citation stats if available
        citation_stats = None
        raw_citation_stats = result.get("citation_stats")
        if raw_citation_stats and isinstance(raw_citation_stats, dict):
            from api.models import CitationStats

            citation_stats = CitationStats(**raw_citation_stats)

        return ChatResponse(
            response=answer,
            sources=sources,
            sources_truncated=sources_truncated,
            session_id=session_id,
            intermediate_steps=intermediate_steps,
            citation_stats=citation_stats,
        )

    except ServiceDegradedError as e:
        logger.warning("Chat degraded: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI assistant is temporarily unavailable. {e}. Please retry in a moment.",
        ) from e
    except Exception as e:
        logger.error(f"Chat processing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat processing failed: {str(e)}",
        ) from e


# ---------------------------------------------------------------------------
# Free Tier Chat Endpoint (no API key required)
# ---------------------------------------------------------------------------

free_router = APIRouter(tags=["Chat (Free Tier)"])


@free_router.post("/chat/free", response_model=ChatResponse, tags=["Chat"])
async def chat_free_endpoint(
    request: ChatRequest,
    req: Request,
    store: Annotated[Optional[Any], Depends(get_vector_store)],
):
    """
    Free tier chat — no API key required.

    Uses the free LLM provider cascade (OpenRouter free → Google Flash → Ollama)
    with hourly/daily rate limits per client IP.
    """
    settings = get_settings()

    if not settings.free_tier_enabled:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Free tier is not enabled. Provide X-API-Key for full access.",
        )

    # Rate limit check
    await _check_free_tier_rate_limit(req)

    # Resolve free tier LLM
    free_llm = get_llm_for_free_user()
    if free_llm is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No free LLM providers available. Please try again later.",
        )

    # Rate limit already checked above
    try:
        agent, sanitized_message, session_id = _build_agent_and_process(
            request, req, free_llm, store
        )
        sources_max_items = max(0, int(settings.chat_sources_max_items))
        sources_max_content_chars = max(0, int(settings.chat_source_content_max_chars))
        sources_max_total_bytes = max(0, int(settings.chat_sources_max_total_bytes))

        result = await asyncio.to_thread(agent.process_query, sanitized_message)

        answer = result.get("answer", "")
        sources, sources_truncated = serialize_chat_sources(
            result.get("source_documents") or [],
            max_items=sources_max_items,
            max_content_chars=sources_max_content_chars,
            max_total_bytes=sources_max_total_bytes,
        )

        return ChatResponse(
            response=answer,
            sources=sources,
            sources_truncated=sources_truncated,
            session_id=session_id,
        )

    except ServiceDegradedError as e:
        logger.warning("Free tier chat degraded: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI assistant is temporarily unavailable. {e}.",
        ) from e
    except Exception as e:
        logger.error(f"Free tier chat failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat processing failed: {str(e)}",
        ) from e
