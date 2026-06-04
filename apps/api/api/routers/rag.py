import hashlib
import json
import logging
import time
import uuid
from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from langchain_core.language_models import BaseChatModel

from api.dependencies import get_knowledge_store, get_rag_qa_llm_details, parse_rag_qa_request
from api.models import RagQaRequest, RagQaResponse, RagResetResponse
from config.settings import get_settings
from core.security_utils import sanitize_for_log
from services.citation_service import CitationService
from utils.document_text_extractor import (
    DocumentTextExtractionError,
    OptionalDependencyMissingError,
    UnsupportedDocumentTypeError,
    extract_text_segments_from_upload,
)
from utils.streaming import (
    HeartbeatConfig,
    StreamMetrics,
    format_sse_event,
    format_sse_heartbeat,
    should_send_heartbeat,
)
from vector_store.knowledge_store import KnowledgeStore

logger = logging.getLogger(__name__)
router = APIRouter(tags=["RAG"])

_READ_CHUNK_BYTES = 1024 * 1024


async def _read_upload_file_limited(file: UploadFile, max_bytes: int) -> tuple[bytes, bool]:
    buf = bytearray()
    while True:
        chunk = await file.read(_READ_CHUNK_BYTES)
        if not chunk:
            return bytes(buf), False
        if len(buf) + len(chunk) > max_bytes:
            return bytes(buf), True
        buf.extend(chunk)


@router.post("/rag/upload", tags=["RAG"])
async def upload_documents(
    files: list[UploadFile],
    store: Annotated[Optional[KnowledgeStore], Depends(get_knowledge_store)],
):
    """
    Upload documents and index for local RAG (CE-safe).
    PDF/DOCX require optional dependencies; unsupported types return a 422 when nothing is indexed.
    """
    if not store:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Knowledge store is not available",
        )

    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    settings = get_settings()
    max_files = max(1, int(getattr(settings, "rag_max_files", 10)))
    max_file_bytes = max(1, int(getattr(settings, "rag_max_file_bytes", 10 * 1024 * 1024)))
    max_total_bytes = max(1, int(getattr(settings, "rag_max_total_bytes", 25 * 1024 * 1024)))

    if len(files) > max_files:
        raise HTTPException(status_code=400, detail=f"Too many files (max {max_files})")

    total_chunks = 0
    total_bytes = 0
    errors: list[str] = []
    buffered: list[tuple[str, str, bytes]] = []

    for f in files:
        try:
            content_type = (f.content_type or "").lower()
            name = f.filename or "unknown"
            data, too_large = await _read_upload_file_limited(f, max_bytes=max_file_bytes)
            if too_large:
                errors.append(f"{name}: File too large (max {max_file_bytes} bytes)")
                continue

            total_bytes += len(data)
            buffered.append((name, content_type, data))
        except Exception as e:
            logger.warning("Failed to read %s: %s", f.filename, e)
            errors.append(f"{f.filename}: {e}")

    if total_bytes > max_total_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={
                "message": "Upload payload too large",
                "max_total_bytes": max_total_bytes,
                "total_bytes": total_bytes,
                "errors": errors,
            },
        )

    for name, content_type, data in buffered:
        try:
            try:
                segments = extract_text_segments_from_upload(
                    filename=name,
                    content_type=content_type,
                    data=data,
                )
            except (UnsupportedDocumentTypeError, OptionalDependencyMissingError) as e:
                errors.append(str(e))
                continue
            except DocumentTextExtractionError as e:
                errors.append(f"{name}: {e}")
                continue

            filtered_segments = [(s.text, s.metadata) for s in segments if (s.text or "").strip()]
            if not filtered_segments:
                errors.append(f"{name}: No extractable text found")
                continue

            try:
                added = store.ingest_text_segments(segments=filtered_segments, source=name)
                total_chunks += added
            except Exception as e:
                logger.warning("Failed to ingest %s: %s", name, e)
                errors.append(f"{name}: {e}")
        except Exception as e:
            logger.warning("Failed to ingest %s: %s", name, e)
            errors.append(f"{name}: {e}")

    if total_chunks == 0 and errors:
        raise HTTPException(
            status_code=422,
            detail={"message": "No documents were indexed", "errors": errors},
        )

    return {"message": "Upload processed", "chunks_indexed": total_chunks, "errors": errors}


@router.post("/rag/reset", tags=["RAG"], response_model=RagResetResponse)
async def reset_rag_knowledge(
    store: Annotated[Optional[KnowledgeStore], Depends(get_knowledge_store)],
):
    """
    Clear all indexed knowledge documents for local RAG (CE-safe).
    """
    if not store:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Knowledge store is not available",
        )

    removed = store.clear()
    stats = store.get_stats()
    return {
        "message": "Knowledge cleared",
        "documents_removed": removed,
        "documents_remaining": int(stats.get("documents", 0)),
    }


@router.post("/rag/qa", tags=["RAG"], response_model=RagQaResponse)
async def rag_qa(
    rag_request: Annotated[RagQaRequest, Depends(parse_rag_qa_request)],
    req: Request,
    store: Annotated[Optional[KnowledgeStore], Depends(get_knowledge_store)],
    llm_details: Annotated[
        tuple[Optional[BaseChatModel], Optional[str], Optional[str]],
        Depends(get_rag_qa_llm_details),
    ],
):
    """
    Simple QA over uploaded knowledge with citations.
    If LLM is unavailable, returns concatenated context as answer.
    Supports SSE streaming when stream=true.
    """
    # Get request_id from middleware for correlation
    request_id = getattr(req.state, "request_id", None) or str(uuid.uuid4())

    # Check response cache for non-streaming requests (Task #55)
    cache = getattr(req.app.state, "response_cache", None)
    if cache and not rag_request.stream:
        body_hash = hashlib.sha256(
            json.dumps(
                {"question": rag_request.question, "top_k": rag_request.top_k},
                sort_keys=True,
            ).encode()
        ).hexdigest()[:16]
        cached = await cache.get(req, body_hash=body_hash)
        if cached and isinstance(cached.data, dict) and "answer" in cached.data:
            return cached.data

    if not store:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Knowledge store is not available",
        )

    llm, effective_provider, effective_model = llm_details
    settings = get_settings()

    results = store.similarity_search_with_score(rag_request.question, k=rag_request.top_k)
    docs = [d for d, _s in results]
    scores = [s for _d, s in results]

    if not docs:
        empty_response: dict[str, Any] = {
            "answer": "",
            "citations": [],
            "citation_format": rag_request.citation_format,
            "citation_stats": None,
            "llm_used": False,
            "provider": effective_provider,
            "model": effective_model,
        }
        if rag_request.stream:

            async def empty_stream():
                yield "event: meta\n"
                yield f"data: {json.dumps(empty_response)}\n\n"
                yield "data: [DONE]\n\n"

            return StreamingResponse(
                empty_stream(),
                media_type="text/event-stream",
                headers={
                    "X-Heartbeat-Interval": str(settings.stream_heartbeat_interval_seconds),
                    "X-Stream-Timeout": str(settings.stream_timeout_seconds),
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )
        return empty_response

    context = "\n\n".join([doc.page_content for doc in docs])

    # Process citations with enhanced extraction
    citation_service = CitationService()
    enhanced_citations = citation_service.process_citations(
        documents=docs,
        scores=scores,
        query=rag_request.question,
        format_style=rag_request.citation_format,
    )
    citation_stats = citation_service.calculate_citation_stats(enhanced_citations)

    # Prepare response data
    base_response = {
        "citations": enhanced_citations,
        "citation_format": rag_request.citation_format,
        "citation_stats": citation_stats,
        "provider": effective_provider,
        "model": effective_model,
    }

    if rag_request.stream:

        async def streaming_response():
            # Initialize streaming configuration
            heartbeat_config = HeartbeatConfig(
                interval_seconds=settings.stream_heartbeat_interval_seconds,
                timeout_seconds=settings.stream_timeout_seconds,
            )
            stream_metrics = StreamMetrics(
                session_id=str(uuid.uuid4()),
                request_id=request_id,
            )
            last_heartbeat = time.time()

            try:
                # Send retrieval progress event
                retrieval_event = {
                    "type": "retrieval",
                    "docs_retrieved": len(docs),
                    "question": rag_request.question,
                }
                yield format_sse_event("progress", json.dumps(retrieval_event, default=str))

                if llm:
                    # Stream LLM response
                    prompt = (
                        "Answer the question based only on the following context.\n\n"
                        f"{context}\n\nQuestion: {rag_request.question}\n\n"
                        "If the answer cannot be found in the context, say you don't know."
                    )

                    # Check if LLM supports streaming
                    if hasattr(llm, "astream"):
                        stream_chunks = llm.astream(prompt)
                        async for chunk in stream_chunks:
                            # Check if heartbeat needed
                            if should_send_heartbeat(last_heartbeat, heartbeat_config):
                                yield format_sse_heartbeat()
                                last_heartbeat = time.time()

                            chunk_text = chunk.content if hasattr(chunk, "content") else str(chunk)
                            chunk_bytes = len(chunk_text.encode("utf-8"))
                            stream_metrics.record_chunk(chunk_bytes)
                            yield f"data: {json.dumps({'content': chunk_text}, ensure_ascii=False)}\n\n"
                    else:
                        # Fallback to non-streaming invoke
                        msg = llm.invoke(prompt)
                        content = getattr(msg, "content", str(msg))
                        yield f"data: {json.dumps({'content': content}, ensure_ascii=False)}\n\n"
                        stream_metrics.record_chunk(len(content.encode("utf-8")))

                    base_response["llm_used"] = True
                else:
                    # No LLM available, stream context snippet
                    snippet = context[:500]
                    yield f"data: {json.dumps({'content': snippet}, ensure_ascii=False)}\n\n"
                    stream_metrics.record_chunk(len(snippet.encode("utf-8")))
                    base_response["llm_used"] = False

                # Mark stream as completed
                stream_metrics.complete()

                # Send meta event with full response
                yield "event: meta\n"
                yield f"data: {json.dumps(base_response, default=str)}\n\n"

                # Send metrics event if enabled
                if settings.stream_metrics_enabled:
                    yield format_sse_event("metrics", json.dumps(stream_metrics.to_dict()))

                yield "data: [DONE]\n\n"

            except Exception as e:
                stream_metrics.record_error()
                logger.error(
                    "RAG stream error (request_id=%s): %s",
                    sanitize_for_log(request_id),
                    sanitize_for_log(e),
                )
                error_payload = {"error": str(e), "request_id": request_id}
                yield "event: error\n"
                yield f"data: {json.dumps(error_payload)}\n\n"
                yield "data: [DONE]\n\n"

        return StreamingResponse(
            streaming_response(),
            media_type="text/event-stream",
            headers={
                "X-Heartbeat-Interval": str(settings.stream_heartbeat_interval_seconds),
                "X-Stream-Timeout": str(settings.stream_timeout_seconds),
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    # Non-streaming path
    if llm:
        try:
            prompt = (
                "Answer the question based only on the following context.\n\n"
                f"{context}\n\nQuestion: {rag_request.question}\n\n"
                "If the answer cannot be found in the context, say you don't know."
            )
            msg = llm.invoke(prompt)
            content = getattr(msg, "content", str(msg))
            base_response["answer"] = content
            base_response["llm_used"] = True
            # Cache non-streaming RAG response (Task #55)
            if cache:
                await cache.set(req, data=base_response, status_code=200, body_hash=body_hash)
            return base_response
        except Exception as e:
            logger.warning("LLM invocation failed: %s", e)

    # Fallback: return context snippet
    snippet = context[:500]
    base_response["answer"] = snippet
    base_response["llm_used"] = False
    # Cache non-streaming fallback response (Task #55)
    if cache:
        await cache.set(req, data=base_response, status_code=200, body_hash=body_hash)
    return base_response
