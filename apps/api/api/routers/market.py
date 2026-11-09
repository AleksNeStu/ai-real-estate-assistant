"""Market analytics API endpoints.

Task #38: Price History & Trends
"""

from typing import Any, Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from analytics.market_insights import MarketInsights
from api.deps.auth import get_current_active_user
from db.database import get_db
from db.models import User
from db.repositories import PriceSnapshotRepository
from db.schemas import (
    AreaComparisonResponse,
    AreaInsightsResponse,
    IntervalType,
    MarketIndicatorsResponse,
    MarketTrendPoint,
    MarketTrendsResponse,
    PriceHistoryResponse,
    PriceSnapshotResponse,
)
from utils.property_cache import load_collection
from utils.response_cache import cached_response

router = APIRouter(prefix="/market", tags=["Market Analytics"])


def _get_vector_store(request: Request):
    """Get vector store from app state."""
    return getattr(request.app.state, "vector_store", None)


@router.get(
    "/price-history/{property_id}",
    response_model=PriceHistoryResponse,
    summary="Get price history for a property",
    description="Get historical price snapshots for a specific property.",
)
async def get_price_history(
    property_id: str,
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum snapshots to return"),
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> PriceHistoryResponse:
    """Get price history for a property."""
    repo = PriceSnapshotRepository(session)
    snapshots = await repo.get_by_property(property_id, limit=limit)
    total = await repo.count_for_property(property_id)

    if not snapshots:
        return PriceHistoryResponse(
            property_id=property_id,
            snapshots=[],
            total=0,
            trend="insufficient_data",
        )

    # Calculate trend (snapshots are ordered by recorded_at desc)
    first = snapshots[-1] if snapshots else None  # Oldest
    last = snapshots[0] if snapshots else None  # Newest

    price_change_percent = None
    trend = "stable"

    if first and last and first.price > 0:
        price_change_percent = ((last.price - first.price) / first.price) * 100
        if abs(price_change_percent) < 2:
            trend = "stable"
        elif price_change_percent > 0:
            trend = "increasing"
        else:
            trend = "decreasing"

    return PriceHistoryResponse(
        property_id=property_id,
        snapshots=[PriceSnapshotResponse.model_validate(s) for s in snapshots],
        total=total,
        current_price=last.price if last else None,
        first_recorded=first.recorded_at if first else None,
        last_recorded=last.recorded_at if last else None,
        price_change_percent=price_change_percent,
        trend=trend,
    )


@router.get(
    "/trends",
    response_model=MarketTrendsResponse,
    summary="Get market trend data",
    description="Get average prices by city/district over time.",
)
@cached_response(ttl_seconds=3600)  # Cache for 1 hour
async def get_market_trends(
    request: Request,
    city: Optional[str] = Query(default=None, description="Filter by city"),
    district: Optional[str] = Query(default=None, description="Filter by district"),
    interval: IntervalType = Query(default="month", description="Interval: month, quarter, year"),
    months_back: int = Query(default=12, ge=1, le=60, description="Months of history"),
    user: User = Depends(get_current_active_user),
) -> MarketTrendsResponse:
    """Get market trend data."""
    # Load properties from cache
    properties = load_collection()
    if not properties or not properties.properties:
        return MarketTrendsResponse(
            city=city,
            district=district,
            interval=interval,
            data_points=[],
            trend_direction="insufficient_data",
            confidence="low",
        )

    # Use existing MarketInsights class
    insights = MarketInsights(properties)

    # Get historical trends
    try:
        historical = insights.get_historical_price_trends(
            interval=interval,
            city=city,
            months_back=months_back,
        )
    except Exception:
        historical = []

    # Get overall trend
    try:
        price_trend = insights.get_price_trend(city=city)
        trend_direction = price_trend.direction.value
        change_percent = price_trend.change_percent
        confidence = price_trend.confidence
    except Exception:
        trend_direction = "stable"
        change_percent = None
        confidence = "low"

    data_points = [
        MarketTrendPoint(
            period=point.period,
            start_date=point.start_date,
            end_date=point.end_date,
            average_price=point.average_price,
            median_price=point.median_price,
            volume=point.volume,
            avg_price_per_sqm=point.avg_price_per_sqm,
            currency=point.currency,
        )
        for point in historical
    ]

    return MarketTrendsResponse(
        city=city,
        district=district,
        interval=interval,
        data_points=data_points,
        trend_direction=trend_direction,
        change_percent=change_percent,
        confidence=confidence,
    )


@router.get(
    "/indicators",
    response_model=MarketIndicatorsResponse,
    summary="Get market indicators",
    description="Get current market health indicators (rising/falling/stable).",
)
@cached_response(ttl_seconds=1800)  # Cache for 30 minutes
async def get_market_indicators(
    request: Request,
    city: Optional[str] = Query(default=None, description="Filter by city"),
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> MarketIndicatorsResponse:
    """Get market indicators."""
    # Get price snapshots for trend calculation
    repo = PriceSnapshotRepository(session)

    # Get recent price drops from snapshots
    try:
        drops = await repo.get_properties_with_price_drops(
            threshold_percent=5.0,
            days_back=7,
        )
        price_drops_7d = len(drops)
    except Exception:
        price_drops_7d = 0

    # Load properties and get market insights
    properties = load_collection()

    if not properties or not properties.properties:
        return MarketIndicatorsResponse(
            city=city,
            overall_trend="stable",
            total_listings=0,
            new_listings_7d=0,
            price_drops_7d=price_drops_7d,
            hottest_districts=[],
            coldest_districts=[],
        )

    try:
        insights = MarketInsights(properties)
        price_trend = insights.get_price_trend(city=city)
        overall_trend = price_trend.direction.value if price_trend else "stable"

        # Map trend direction to market trend type
        if overall_trend == "increasing":
            overall_trend = "rising"
        elif overall_trend == "decreasing":
            overall_trend = "falling"
        else:
            overall_trend = "stable"
    except Exception:
        overall_trend = "stable"

    # Get district-level data
    hottest_districts: list[dict[str, Any]] = []
    coldest_districts: list[dict[str, Any]] = []

    try:
        city_indices = insights.get_city_price_indices()
        if city_indices is not None and not city_indices.empty:
            # Sort by average price
            sorted_cities = city_indices.sort_values("avg_price", ascending=False)

            hottest_districts = [
                {
                    "name": str(row.get("city", "Unknown")),
                    "avg_price": float(row.get("avg_price", 0)),
                    "count": int(row.get("count", 0)),
                }
                for _, row in sorted_cities.head(5).iterrows()
            ]

            coldest_districts = [
                {
                    "name": str(row.get("city", "Unknown")),
                    "avg_price": float(row.get("avg_price", 0)),
                    "count": int(row.get("count", 0)),
                }
                for _, row in sorted_cities.tail(5).iterrows()
            ]
    except Exception:
        pass

    return MarketIndicatorsResponse(
        city=city,
        overall_trend=overall_trend,
        avg_price_change_1m=None,  # Would need snapshot data comparison
        avg_price_change_3m=None,
        avg_price_change_6m=None,
        avg_price_change_1y=None,
        total_listings=properties.total_count if properties else 0,
        new_listings_7d=0,  # Would need comparison with previous state
        price_drops_7d=price_drops_7d,
        hottest_districts=hottest_districts,
        coldest_districts=coldest_districts,
    )


@router.get(
    "/compare",
    response_model=AreaComparisonResponse,
    summary="Compare two areas",
    description="Compare market metrics between two cities/areas side by side.",
)
@cached_response(ttl_seconds=3600)  # Cache for 1 hour
async def compare_areas(
    request: Request,
    city1: str = Query(..., description="First city to compare"),
    city2: str = Query(..., description="Second city to compare"),
    user: User = Depends(get_current_active_user),
) -> AreaComparisonResponse:
    """Compare market metrics between two areas."""

    from db.schemas import AreaComparisonResponse, AreaInsightsResponse

    # Load properties from cache
    properties = load_collection()

    if not properties or not properties.properties:
        # Return empty comparison if no data
        return AreaComparisonResponse(
            area1=AreaInsightsResponse(
                city=city1,
                property_count=0,
                avg_price=0,
                median_price=0,
            ),
            area2=AreaInsightsResponse(
                city=city2,
                property_count=0,
                avg_price=0,
                median_price=0,
            ),
            price_difference=0,
            price_difference_percent=0,
            cheaper_area=city1,
            more_properties_area=city1,
        )

    # Use MarketInsights for comparison
    insights = MarketInsights(properties)

    try:
        comparison = insights.compare_locations(city1, city2)

        if "error" in comparison:
            # One or both cities not found
            comparison.get("city1", city1)
            comparison.get("city2", city2)

            return AreaComparisonResponse(
                area1=AreaInsightsResponse(
                    city=city1,
                    property_count=0,
                    avg_price=0,
                    median_price=0,
                ),
                area2=AreaInsightsResponse(
                    city=city2,
                    property_count=0,
                    avg_price=0,
                    median_price=0,
                ),
                price_difference=0,
                price_difference_percent=0,
                cheaper_area=city1,
                more_properties_area=city1,
            )

        # Build response from comparison data
        area1_insights = comparison.get("city1", {})
        area2_insights = comparison.get("city2", {})

        return AreaComparisonResponse(
            area1=AreaInsightsResponse(
                city=area1_insights.get("city", city1),
                property_count=area1_insights.get("property_count", 0),
                avg_price=area1_insights.get("avg_price", 0),
                median_price=area1_insights.get("median_price", 0),
                avg_price_per_sqm=area1_insights.get("avg_price_per_sqm"),
                most_common_room_count=area1_insights.get("most_common_room_count"),
                amenity_availability=area1_insights.get("amenity_availability", {}),
                price_comparison=area1_insights.get("price_comparison"),
                currency=area1_insights.get("currency"),
            ),
            area2=AreaInsightsResponse(
                city=area2_insights.get("city", city2),
                property_count=area2_insights.get("property_count", 0),
                avg_price=area2_insights.get("avg_price", 0),
                median_price=area2_insights.get("median_price", 0),
                avg_price_per_sqm=area2_insights.get("avg_price_per_sqm"),
                most_common_room_count=area2_insights.get("most_common_room_count"),
                amenity_availability=area2_insights.get("amenity_availability", {}),
                price_comparison=area2_insights.get("price_comparison"),
                currency=area2_insights.get("currency"),
            ),
            price_difference=comparison.get("price_difference", 0),
            price_difference_percent=comparison.get("price_difference_percent", 0),
            cheaper_area=comparison.get("cheaper_area", city1),
            more_properties_area=comparison.get("more_properties", city1),
        )

    except Exception:
        # Fallback response on error
        return AreaComparisonResponse(
            area1=AreaInsightsResponse(
                city=city1,
                property_count=0,
                avg_price=0,
                median_price=0,
            ),
            area2=AreaInsightsResponse(
                city=city2,
                property_count=0,
                avg_price=0,
                median_price=0,
            ),
            price_difference=0,
            price_difference_percent=0,
            cheaper_area=city1,
            more_properties_area=city1,
        )


@router.get(
    "/area/{city}",
    response_model=AreaInsightsResponse,
    summary="Get insights for a single area",
    description="Get detailed market insights for a specific city/area.",
)
@cached_response(ttl_seconds=3600)  # Cache for 1 hour
async def get_area_insights(
    city: str,
    request: Request,
    user: User = Depends(get_current_active_user),
) -> AreaInsightsResponse:
    """Get detailed market insights for a specific area."""
    from db.schemas import AreaInsightsResponse

    # Load properties from cache
    properties = load_collection()

    if not properties or not properties.properties:
        return AreaInsightsResponse(
            city=city,
            property_count=0,
            avg_price=0,
            median_price=0,
        )

    # Use MarketInsights for area data
    insights = MarketInsights(properties)

    try:
        location_insights = insights.get_location_insights(city)

        if location_insights is None:
            return AreaInsightsResponse(
                city=city,
                property_count=0,
                avg_price=0,
                median_price=0,
            )

        return AreaInsightsResponse(
            city=location_insights.city,
            property_count=location_insights.property_count,
            avg_price=location_insights.avg_price,
            median_price=location_insights.median_price,
            avg_price_per_sqm=location_insights.avg_price_per_sqm,
            most_common_room_count=location_insights.most_common_room_count,
            amenity_availability=location_insights.amenity_availability,
            price_comparison=location_insights.price_comparison,
            currency=location_insights.currency,
        )

    except Exception:
        return AreaInsightsResponse(
            city=city,
            property_count=0,
            avg_price=0,
            median_price=0,
        )
