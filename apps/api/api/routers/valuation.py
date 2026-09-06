"""
v5.1: AI Property Valuation with Multi-Year Price Forecast and
AI Neighborhood One-Liner endpoints.

These endpoints complement the existing /tools/valuation CE stub by
providing an LLM-only forecast and a 2-3 sentence neighborhood summary.
They work in demo mode without any external paid APIs.
"""

from __future__ import annotations

import logging
from typing import Annotated, Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from langchain_core.language_models import BaseChatModel

from api.dependencies import get_llm, get_vector_store
from api.models import (
    ForecastPointResponse,
    NeighborhoodSummaryRequest,
    NeighborhoodSummaryResponse,
    PriceForecastRequest,
    PriceForecastResponse,
)
from tools.neighborhood_summary import NeighborhoodSummaryTool
from tools.price_forecast_tools import (
    PriceForecastResult,
    PriceForecastTool,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Valuation"])


def _to_float(value: object) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _to_int(value: object) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(float(value))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _load_property_features(
    store: Any, property_id: str
) -> Optional[Dict[str, Any]]:
    if store is None or not property_id:
        return None
    try:
        docs = store.get_properties_by_ids([property_id])
    except Exception as e:
        # codeql[py/log-injection]: user input escaped via %r (repr) so
        # embedded newlines/control chars cannot split the log line.
        # See tests/integration/test_valuation_router.py::
        # test_log_injection_in_property_id_is_escaped for the regression
        # test that proves the mitigation.
        logger.warning("Failed to load property %r: %s", property_id, e)
        return None
    if not docs:
        return None
    md = getattr(docs[0], "metadata", None) or {}
    return {
        "id": md.get("id") or property_id,
        "city": md.get("city"),
        "neighborhood": md.get("neighborhood"),
        "country": md.get("country"),
        "property_type": md.get("property_type"),
        "area_sqm": _to_float(md.get("area_sqm")),
        "rooms": _to_float(md.get("rooms")),
        "bathrooms": _to_float(md.get("bathrooms")),
        "year_built": _to_int(md.get("year_built")),
        "price": _to_float(md.get("price")),
        "price_per_sqm": _to_float(md.get("price_per_sqm")),
        "latitude": _to_float(md.get("lat") or md.get("latitude")),
        "longitude": _to_float(md.get("lon") or md.get("longitude")),
        "currency": md.get("currency") or "EUR",
    }


def _validate_request(req: PriceForecastRequest) -> List[int]:
    if not req.property_id and not req.property_features:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either property_id or property_features must be provided",
        )
    if not req.horizon_years:
        return [1, 3, 5]
    out: List[int] = []
    seen: set[int] = set()
    for y in req.horizon_years:
        try:
            iy = int(y)
        except (TypeError, ValueError):
            continue
        if 1 <= iy <= 10 and iy not in seen:
            seen.add(iy)
            out.append(iy)
    return sorted(out) or [1, 3, 5]


@router.post(
    "/tools/price-forecast",
    response_model=PriceForecastResponse,
    tags=["Valuation"],
)
async def price_forecast(
    request: PriceForecastRequest,
    store: Annotated[Any, Depends(get_vector_store)],
    _llm: Annotated[BaseChatModel, Depends(get_llm)],
) -> PriceForecastResponse:
    """Estimate current value and project value at the requested horizons.

    Either `property_id` (resolved from the vector store) OR `property_features`
    must be supplied. The LLM returns a structured estimate with confidence and
    drivers; a deterministic fallback is used if the LLM is unavailable.
    """
    horizons = _validate_request(request)
    features: Dict[str, Any] = {}
    if request.property_id:
        loaded = _load_property_features(store, request.property_id)
        if loaded is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Property {request.property_id} not found",
            )
        features.update(loaded)
    if request.property_features:
        features.update(request.property_features)

    tool = PriceForecastTool(vector_store=store, llm=_llm)
    try:
        result: PriceForecastResult = tool.forecast(
            {
                "property_id": request.property_id,
                "property_features": features,
                "horizon_years": horizons,
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Price forecast failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Forecast failed: {e}",
        ) from e
    return PriceForecastResponse(
        current_estimate=result.current_estimate,
        currency=result.currency,
        horizon_years=result.horizon_years,
        forecast=[
            ForecastPointResponse(
                years_ahead=p.years_ahead,
                estimated_value=p.estimated_value,
                lower_bound=p.lower_bound,
                upper_bound=p.upper_bound,
            )
            for p in result.forecast
        ],
        confidence=result.confidence,
        drivers=result.drivers,
        explanation=result.explanation,
        comparables_used=result.comparables_used,
        median_price_per_sqm=result.median_price_per_sqm,
        neighborhood_median_price_per_sqm=result.neighborhood_median_price_per_sqm,
        disclaimer=result.disclaimer,
    )


@router.post(
    "/tools/neighborhood-summary",
    response_model=NeighborhoodSummaryResponse,
    tags=["Valuation"],
)
async def neighborhood_summary(
    request: NeighborhoodSummaryRequest,
    _llm: Annotated[BaseChatModel, Depends(get_llm)],
) -> NeighborhoodSummaryResponse:
    """Return a 2-3 sentence AI summary of a neighborhood."""
    if not request.city and not request.neighborhood:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either city or neighborhood must be provided",
        )
    tool = NeighborhoodSummaryTool(llm=_llm)
    try:
        text = tool.summarize(
            {
                "city": request.city,
                "neighborhood": request.neighborhood,
                "property_type": request.property_type,
                "rooms": request.rooms,
                "area_sqm": request.area_sqm,
                "language": request.language,
                "max_sentences": request.max_sentences,
            }
        )
    except Exception as e:
        logger.exception("Neighborhood summary failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Neighborhood summary failed: {e}",
        ) from e
    return NeighborhoodSummaryResponse(summary=text, language=request.language)