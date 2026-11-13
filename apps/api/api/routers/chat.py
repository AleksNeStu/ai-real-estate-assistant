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
from agents.intent_prompts import build_buyer_memory_block
from agents.memory_extractor import extract_buyer_facts
from ai.memory import (
    get_context_manager,
    get_optimized_memory,
    init_context_manager,
)
from api.chat_sources import serialize_chat_sources, serialize_web_sources
from api.dependencies import get_buyer_memory_service, get_llm, get_vector_store
from api.deps.auth import get_optional_user
from api.models import ChatRequest, ChatResponse
from config.settings import get_settings
from core.circuit_breaker import ServiceDegradedError
from db.models import User
from services.buyer_memory_service import BuyerMemoryService
from utils.free_tier import client_ip, get_free_tier_rate_limiter, get_llm_for_free_user
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
from utils.tool_calls import build_tool_calls_from_steps

logger = logging.getLogger(__name__)


def _tool_call_of(chunk: str) -> dict | None:
    """The tool call a streamed chunk carries, if it carries one.

    The agent reports the calls it made as data: a JSON object with a
    `tool_call` key. Every other chunk is the answer's text and travels on
    to the client untouched.
    """
    if "tool_call" not in chunk:
        return None
    try:
        payload = json.loads(chunk)
    except (TypeError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    call = payload.get("tool_call")
    return call if isinstance(call, dict) else None


def _answer_text_of(chunk: str) -> str:
    """The prose a streamed chunk carries, if it carries any.

    The agent streams JSON envelopes (``{"content": "..."}``), and the buyer
    memory extractor reads prose: handing it the envelopes would make it
    reason over JSON fragments instead of over the answer.

    Args:
        chunk: One streamed chunk.

    Returns:
        The answer's text. A chunk that is not an envelope travels as it is.
    """
    try:
        payload = json.loads(chunk)
    except (TypeError, ValueError):
        return chunk
    if isinstance(payload, dict):
        content = payload.get("content")
        if isinstance(content, str):
            return content
    return chunk


router = APIRouter(tags=["Chat"])


async def _check_free_tier_rate_limit(req: Request) -> None:
    """Enforce free tier rate limits keyed by client IP."""
    limiter = get_free_tier_rate_limiter()
    allowed, reason, retry_after = await limiter.check(client_ip(req))
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Free tier rate limit: {reason}. Retry after {retry_after}s.",
            headers={"Retry-After": str(retry_after)},
        )


def _request_is_anonymous(req: Request) -> bool:
    """True when the request carries no session of its own.

    The API key identifies the deployment, not the visitor: the frontend
    proxy injects it for every browser request, so its presence says nothing
    about who is calling. The session token is what says a visitor signed in.

    The counting applies only where the deployment is open — with the API-key
    bypass on, the key dependency lets every visitor through, and a public
    demo whose model is a paid key would otherwise be an open wallet. A
    private deployment keeps its own traffic.
    """
    settings = get_settings()
    if not settings.demo_api_key_bypass:
        return False

    if req.cookies.get("access_token"):
        return False

    authorization = (req.headers.get("authorization") or "").strip()
    if authorization.lower().startswith("bearer "):
        return False

    return True


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


# ---------------------------------------------------------------------------
# The buyer's memory (Task #79)
#
# The chat path both READS the memory (the answer uses what the buyer has
# already told us) and WRITES it (the turn teaches the memory). An anonymous
# visitor has no account and therefore no memory: their prompt is exactly the
# prompt of before the memory existed.
#
# The failure policy is the contract: neither the read nor the write may ever
# fail the answer. A broken recall answers without the memory; a broken
# extraction loses the facts of the turn and is logged.
# ---------------------------------------------------------------------------


async def _recall_buyer_memory(
    memory_service: BuyerMemoryService,
    user: Optional[User],
    query: str,
) -> str:
    """The block of what this buyer has already told us - or nothing.

    A failure to recall never fails the answer: the turn is answered without
    the memory, exactly as it was answered before the memory existed.
    """
    if user is None:
        return ""

    try:
        facts = await memory_service.recall_for_user(user.id, query=query)
        if not facts:
            return ""
        return build_buyer_memory_block(facts)
    except Exception as exc:
        logger.warning("Buyer memory read failed, answering without it: %s", exc)
        return ""


async def _write_buyer_memory(
    memory_service: BuyerMemoryService,
    user: Optional[User],
    messages: list[dict[str, str]],
    answer: Any,
    listings: list[dict[str, Any]],
    llm: Optional[BaseChatModel],
) -> None:
    """Teach the buyer's memory what this turn taught us.

    The same model that answered the turn reads it - one provider, never a
    second one. A failure here never fails the answer: the facts of the turn
    are lost and the turn is answered normally.
    """
    if user is None:
        return
    if llm is None:
        logger.debug("Buyer memory extraction skipped: the chat path has no LLM")
        return

    try:
        facts = await extract_buyer_facts(
            messages=messages,
            answer=answer,
            listings=listings,
            llm=llm,
        )
        for fact in facts:
            await memory_service.record_fact(
                user_id=user.id,
                kind=fact.kind,
                content=fact.content,
                listing_id=fact.listing_id,
                confidence=fact.confidence,
                source="chat",
            )
        logger.debug("Buyer memory: %d durable facts recorded", len(facts))
    except Exception as exc:
        logger.warning("Buyer memory write failed, the answer is unaffected: %s", exc)


def _listing_payloads(sources: Any) -> list[dict[str, Any]]:
    """The listings of a turn, in the shape the extractor reads them in."""
    payloads: list[dict[str, Any]] = []
    for source in sources or []:
        if not isinstance(source, dict):
            continue
        metadata = source.get("metadata")
        if isinstance(metadata, dict) and metadata.get("id"):
            payloads.append(metadata)
    return payloads


def _turn_listings(result: dict) -> list[dict[str, Any]]:
    """The listings this turn showed - the documents and the web sources."""
    payloads: list[dict[str, Any]] = []

    for document in result.get("source_documents") or []:
        metadata = getattr(document, "metadata", None)
        if isinstance(metadata, dict) and metadata.get("id"):
            payloads.append(metadata)

    payloads.extend(_listing_payloads(result.get("sources")))
    return payloads


def _agent_listings(agent: Any) -> list[dict[str, Any]]:
    """The listings the agent's answer was built from.

    The streaming path yields strings only, so the agent keeps the documents
    it retrieved: without them the caller would have to run a SECOND
    retrieval to learn what the answer was made of - and a second retrieval
    is a different answer (a different query, a different k). The listing a
    buyer read in the prose must be a listing the buyer can speak about.
    """
    payloads: list[dict[str, Any]] = []
    for document in getattr(agent, "last_source_documents", None) or []:
        metadata = getattr(document, "metadata", None)
        if isinstance(metadata, dict) and metadata.get("id"):
            payloads.append(metadata)
    return payloads


def _supports_buyer_memory(agent: Any, method: str) -> bool:
    """Whether the agent's method takes the buyer's memory.

    The agent that answers the turn is the one that owns the wording of the
    prompt, so the router only hands it the block - and only when it takes
    one. An agent that does not is called exactly as it was called before.
    """
    handler = getattr(agent, method, None)
    if handler is None:
        return False
    try:
        parameters = inspect.signature(handler).parameters
    except (TypeError, ValueError):
        return False
    if "buyer_memory" in parameters:
        return True
    return any(p.kind == inspect.Parameter.VAR_KEYWORD for p in parameters.values())


async def _process_with_memory(agent: Any, message: str, memory_block: str) -> dict:
    """Ask the agent, with the memory when there is one."""
    if memory_block and _supports_buyer_memory(agent, "process_query"):
        return await asyncio.to_thread(agent.process_query, message, buyer_memory=memory_block)
    return await asyncio.to_thread(agent.process_query, message)


def _astream_with_memory(agent: Any, message: str, memory_block: str) -> Any:
    """Stream the agent's answer, with the memory when there is one."""
    if memory_block and _supports_buyer_memory(agent, "astream_query"):
        return agent.astream_query(message, buyer_memory=memory_block)
    return agent.astream_query(message)


@router.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat_endpoint(
    request: ChatRequest,
    req: Request,
    llm: Annotated[BaseChatModel, Depends(get_llm)],
    store: Annotated[Optional[Any], Depends(get_vector_store)],
    memory_service: Annotated[BuyerMemoryService, Depends(get_buyer_memory_service)],
    user: Annotated[Optional[User], Depends(get_optional_user)],
):
    """
    Process a chat message using the hybrid agent with session persistence.
    Requires API key authentication.
    """
    settings = get_settings()
    request_id = getattr(req.state, "request_id", None) or str(uuid.uuid4())

    if _request_is_anonymous(req):
        await _check_free_tier_rate_limit(req)

    # An anonymous visitor has no account: no memory is read and none is
    # written, and the prompt is exactly the prompt of before the memory.
    memory_user = None if user is None or _request_is_anonymous(req) else user

    try:
        agent, sanitized_message, session_id = _build_agent_and_process(request, req, llm, store)
        memory_block = await _recall_buyer_memory(memory_service, memory_user, sanitized_message)
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
                    "tool_calls": [],
                }
                # The tool calls the agent made, as data. They travel in the
                # meta event, so the client reads one event and not two.
                tool_calls: list[dict] = []
                # The answer of this turn, as it is streamed, so the turn can
                # teach the buyer's memory what it taught us.
                answer_parts: list[str] = []

                try:
                    # Add timeout protection for streaming
                    with anyio.fail_after(settings.stream_timeout_seconds):
                        if requires_web:
                            result = await _process_with_memory(
                                agent, sanitized_message, memory_block
                            )
                            raw_answer = result.get("answer", "")
                            answer_text = (
                                raw_answer if isinstance(raw_answer, str) else str(raw_answer)
                            )
                            if answer_text:
                                # Record metrics for web path
                                chunk_bytes = len(answer_text.encode("utf-8"))
                                stream_metrics.record_chunk(chunk_bytes)
                                answer_parts.append(answer_text)
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
                                # The calls also travel as data, so the client
                                # draws the card from the fields instead of
                                # parsing the step.
                                sources_payload["tool_calls"] = build_tool_calls_from_steps(
                                    raw_steps
                                )
                        else:
                            async for chunk in _astream_with_memory(
                                agent, sanitized_message, memory_block
                            ):
                                # The agent reports the tool calls it made as
                                # data. They are collected here and travel in
                                # the meta event - the client reads one event.
                                call = _tool_call_of(chunk)
                                if call is not None:
                                    tool_calls.append(call)
                                    continue
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
                                if isinstance(chunk, str):
                                    answer_parts.append(_answer_text_of(chunk))
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

                        sources_payload["tool_calls"] = tool_calls

                        # The turn is answered: what it taught us is written
                        # to the buyer's memory.
                        await _write_buyer_memory(
                            memory_service,
                            memory_user,
                            [{"role": "user", "content": sanitized_message}],
                            "".join(answer_parts),
                            # The documents the answer was built from, and the
                            # citations - the same shape the non-streaming
                            # path validates against.
                            _agent_listings(agent)
                            + _listing_payloads(sources_payload.get("sources")),
                            llm,
                        )

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

        result = await _process_with_memory(agent, sanitized_message, memory_block)

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

        # The turn is answered: what it taught us is written to the buyer's
        # memory. A failure here never fails the answer.
        await _write_buyer_memory(
            memory_service,
            memory_user,
            [{"role": "user", "content": sanitized_message}],
            answer,
            _turn_listings(result),
            llm,
        )

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
    memory_service: Annotated[BuyerMemoryService, Depends(get_buyer_memory_service)],
    user: Annotated[Optional[User], Depends(get_optional_user)],
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

    # An anonymous visitor has no account: no memory is read and none is
    # written, and the prompt is exactly the prompt of before the memory.
    memory_user = None if user is None or _request_is_anonymous(req) else user

    # Rate limit already checked above
    try:
        agent, sanitized_message, session_id = _build_agent_and_process(
            request, req, free_llm, store
        )
        memory_block = await _recall_buyer_memory(memory_service, memory_user, sanitized_message)
        sources_max_items = max(0, int(settings.chat_sources_max_items))
        sources_max_content_chars = max(0, int(settings.chat_source_content_max_chars))
        sources_max_total_bytes = max(0, int(settings.chat_sources_max_total_bytes))

        result = await _process_with_memory(agent, sanitized_message, memory_block)

        answer = result.get("answer", "")
        sources, sources_truncated = serialize_chat_sources(
            result.get("source_documents") or [],
            max_items=sources_max_items,
            max_content_chars=sources_max_content_chars,
            max_total_bytes=sources_max_total_bytes,
        )

        # The turn is answered: what it taught us is written to the buyer's
        # memory. A failure here never fails the answer.
        await _write_buyer_memory(
            memory_service,
            memory_user,
            [{"role": "user", "content": sanitized_message}],
            answer,
            _turn_listings(result),
            free_llm,
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
