import hashlib
import json
import logging
import math
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse

from api.dependencies import get_vector_store
from api.models import (
    RankingExplanation,
    SearchRequest,
    SearchResponse,
    SearchResultItem,
)
from core.circuit_breaker import ServiceDegradedError, get_breaker
from core.security_utils import sanitize_for_log
from data.schemas import Property
from services.ranking_explainer import create_ranking_explainer
from utils.sanitization import sanitize_search_query
from vector_store.chroma_store import ChromaPropertyStore

# Configure logger
logger = logging.getLogger(__name__)

router = APIRouter(tags=["Search"])

# Polygon validation constants
POLYGON_MAX_VERTICES = 100
POLYGON_MAX_AREA_SQKM = 10000  # ~100km radius max


def _validate_polygon(polygon: list[list[list[float]]]) -> Optional[str]:
    """
    Validate polygon for search operations.
    Returns error message if invalid, None if valid.
    """
    if not polygon or len(polygon) == 0:
        return "Polygon coordinates are empty"

    # Get the outer ring (first array)
    outer_ring = polygon[0] if isinstance(polygon[0], list) else polygon
    if not outer_ring or len(outer_ring) < 3:
        return "Polygon must have at least 3 vertices"

    vertex_count = len(outer_ring)
    if vertex_count > POLYGON_MAX_VERTICES:
        return f"Polygon has too many vertices ({vertex_count}, max {POLYGON_MAX_VERTICES})"

    # Calculate approximate area using spherical excess formula
    area = 0.0
    earth_radius_km = 6371.0
    n = len(outer_ring)

    for i in range(n):
        j = (i + 1) % n
        lat1 = math.radians(outer_ring[i][1])
        lat2 = math.radians(outer_ring[j][1])
        lon_diff = math.radians(outer_ring[j][0] - outer_ring[i][0])
        area += lon_diff * (2 + math.sin(lat1) + math.sin(lat2))

    area = abs(area * earth_radius_km * earth_radius_km / 2)

    if area > POLYGON_MAX_AREA_SQKM:
        return f"Polygon area too large ({int(area)} km², max {POLYGON_MAX_AREA_SQKM} km²)"

    return None


def _convert_explanation_to_response(
    explanation,
) -> RankingExplanation:
    """Convert RankingExplanation dataclass to Pydantic model."""
    from api.models import ScoreComponent

    components = [
        ScoreComponent(
            name=c.name,
            value=c.value,
            weight=c.weight,
            contribution=c.contribution,
            description=c.description,
        )
        for c in explanation.components
    ]

    return RankingExplanation(
        property_id=explanation.property_id,
        final_score=explanation.final_score,
        rank=explanation.rank,
        semantic_score=explanation.semantic_score,
        keyword_score=explanation.keyword_score,
        hybrid_score=explanation.hybrid_score,
        exact_match_boost=explanation.exact_match_boost,
        metadata_match_boost=explanation.metadata_match_boost,
        quality_boost=explanation.quality_boost,
        personalization_boost=explanation.personalization_boost,
        diversity_penalty=explanation.diversity_penalty,
        components=components,
    )


@router.post("/search", response_model=SearchResponse, tags=["Search"])
async def search_properties(
    request_body: SearchRequest,
    http_request: Request,
    store: Annotated[Optional[ChromaPropertyStore], Depends(get_vector_store)],
):
    """
    Search for properties using semantic search and metadata filters.
    Results are cached for 5 minutes (TTL 300s).
    """
    # Check response cache (Task #55)
    cache = getattr(http_request.app.state, "response_cache", None)
    if cache:
        body_hash = hashlib.sha256(
            json.dumps(request_body.model_dump(), sort_keys=True, default=str).encode()
        ).hexdigest()[:16]
        cached = await cache.get(http_request, body_hash=body_hash)
        if cached:
            response_data = cached.data
            if isinstance(response_data, dict) and "results" in response_data:
                resp = JSONResponse(content=response_data)
                resp.headers["X-Cache"] = "HIT"
                return resp

    if not store:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Search is temporarily unavailable. The property database is offline. Please try again in a moment.",
        )

    # Use circuit breaker for vector store calls (Task #96)
    breaker = get_breaker("vector_store")

    # Sanitize search query to prevent injection attacks
    try:
        sanitized_query = sanitize_search_query(request_body.query)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from None

    # Validate polygon if provided
    if request_body.polygon:
        polygon_error = _validate_polygon(request_body.polygon)
        if polygon_error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid polygon: {polygon_error}",
            )

    try:
        # Perform hybrid search (Vector + Keyword) with circuit breaker
        async def _do_search():
            return store.hybrid_search(
                query=sanitized_query,
                k=request_body.limit,
                filters=request_body.filters,
                alpha=request_body.alpha,
                lat=request_body.lat,
                lon=request_body.lon,
                radius_km=request_body.radius_km,
                min_lat=request_body.min_lat,
                max_lat=request_body.max_lat,
                min_lon=request_body.min_lon,
                max_lon=request_body.max_lon,
                polygon=request_body.polygon,
                sort_by=request_body.sort_by.value if request_body.sort_by else None,
                sort_order=request_body.sort_order.value if request_body.sort_order else None,
            )

        try:
            results = await breaker.call(_do_search)
        except ServiceDegradedError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Search is temporarily degraded: {e}. Please retry in a moment.",
            ) from e

        # Generate explanations if requested
        explanations = []
        if request_body.include_explanation:
            explainer = create_ranking_explainer()
            explanations = explainer.explain_results(
                results=results,
                query=sanitized_query,
                user_criteria=request_body.filters,
            )

        items = []
        for idx, (doc, score) in enumerate(results):
            try:
                # Document metadata contains property fields
                # We need to handle potential data inconsistencies
                metadata = doc.metadata.copy()

                # Ensure 'id' is present (sometimes stored as doc-id in Chroma)
                if "id" not in metadata:
                    metadata["id"] = "unknown"

                # 'rooms' might be stored as float in Chroma metadata
                # (no int type support sometimes)
                # Pydantic handles this conversion usually

                # Construct Property model
                # validation_error might occur if metadata is incomplete
                prop = Property.model_validate(metadata)

                # Include explanation if available
                explanation_model = None
                if request_body.include_explanation and idx < len(explanations):
                    explanation_model = _convert_explanation_to_response(explanations[idx])

                items.append(
                    SearchResultItem(
                        property=prop,
                        score=score,
                        explanation=explanation_model,
                    )
                )
            except Exception as e:
                logger.warning(
                    "Failed to parse property from search result: %s", sanitize_for_log(e)
                )
                continue

        response = SearchResponse(results=items, count=len(items))

        # Store in cache (Task #55)
        if cache:
            await cache.set(
                http_request,
                data=response.model_dump(mode="json"),
                status_code=200,
                body_hash=body_hash,
            )

        return response

    except Exception as e:
        logger.error("Search failed: %s", sanitize_for_log(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search operation failed: {str(e)}",
        ) from e
