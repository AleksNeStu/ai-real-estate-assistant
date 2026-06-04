"""Comparative Market Analysis (CMA) router.

Provides endpoints for generating CMA reports including comparable
property selection, adjustment calculations, and PDF report export.
"""

import logging
from io import BytesIO
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from analytics.comparable_selector import ComparableSelector
from api.dependencies import get_vector_store
from api.deps.auth import get_current_active_user
from core.security_utils import sanitize_for_log
from data.schemas import Property, PropertyCollection
from db.database import get_db
from db.models import User
from db.repositories import CMAReportRepository
from db.schemas import (
    CMAComparableResponse,
    CMAReportCreate,
    CMAReportListResponse,
    CMAReportResponse,
    CMAValuationResponse,
)
from vector_store.chroma_store import ChromaPropertyStore

logger = logging.getLogger(__name__)

router = APIRouter(tags=["CMA"])


def _document_to_property(doc: Any) -> Property:
    """Convert a ChromaDB Document to a Property object."""
    metadata = doc.metadata or {}
    return Property(
        id=str(metadata.get("id", "")),
        title=metadata.get("title"),
        description=doc.page_content,
        property_type=metadata.get("property_type"),
        listing_type=metadata.get("listing_type"),
        price=metadata.get("price"),
        area_sqm=metadata.get("area_sqm"),
        rooms=metadata.get("rooms"),
        bathrooms=metadata.get("bathrooms"),
        city=metadata.get("city"),
        district=metadata.get("district"),
        neighborhood=metadata.get("neighborhood"),
        latitude=metadata.get("latitude"),
        longitude=metadata.get("longitude"),
        year_built=metadata.get("year_built"),
        floor=metadata.get("floor"),
        total_floors=metadata.get("total_floors"),
        energy_rating=metadata.get("energy_rating"),
        has_parking=metadata.get("has_parking"),
        has_garden=metadata.get("has_garden"),
        has_elevator=metadata.get("has_elevator"),
        has_balcony=metadata.get("has_balcony"),
        is_furnished=metadata.get("is_furnished"),
        has_pool=metadata.get("has_pool"),
        has_garage=metadata.get("has_garage"),
        pets_allowed=metadata.get("pets_allowed"),
    )


# ============================================================================
# Helper Functions
# ============================================================================


def _property_to_dict(prop: Property) -> dict[str, Any]:
    """Convert Property object to dictionary for storage."""
    return {
        "id": prop.id,
        "title": prop.title,
        "property_type": prop.property_type,
        "listing_type": prop.listing_type,
        "price": prop.price,
        "area_sqm": prop.area_sqm,
        "rooms": prop.rooms,
        "bedrooms": prop.bedrooms,
        "bathrooms": prop.bathrooms,
        "city": prop.city,
        "district": prop.district,
        "neighborhood": prop.neighborhood,
        "street": prop.street,
        "latitude": prop.latitude,
        "longitude": prop.longitude,
        "year_built": prop.year_built,
        "floor": prop.floor,
        "total_floors": prop.total_floors,
        "energy_rating": prop.energy_rating,
        "has_parking": prop.has_parking,
        "has_garden": prop.has_garden,
        "has_elevator": prop.has_elevator,
        "has_balcony": prop.has_balcony,
        "is_furnished": prop.is_furnished,
        "has_pool": prop.has_pool,
        "has_garage": prop.has_garage,
        "pets_allowed": prop.pets_allowed,
    }


def _calculate_valuation(
    subject: Property,
    adjusted_comparables: list[dict[str, Any]],
) -> CMAValuationResponse:
    """Calculate final valuation from adjusted comparables."""
    if not adjusted_comparables:
        return CMAValuationResponse(
            estimated_value=subject.price or 0.0,
            value_range_low=subject.price or 0.0,
            value_range_high=subject.price or 0.0,
            confidence_score=0.0,
            price_per_sqm=0.0,
            comparables_count=0,  # type: ignore[call-arg]
            avg_adjusted_price=0.0,  # type: ignore[call-arg]
            median_adjusted_price=0.0,  # type: ignore[call-arg]
            std_deviation=0.0,  # type: ignore[call-arg]
        )

    # Weight by similarity score
    total_weight = 0.0
    weighted_sum = 0.0

    prices = []
    for comp in adjusted_comparables:
        weight = comp.get("similarity_score", 50) / 100.0
        adjusted_price = comp.get("adjusted_price", 0)
        weighted_sum += adjusted_price * weight
        total_weight += weight
        prices.append(adjusted_price)

    # Calculate estimated value
    if total_weight > 0:
        estimated_value = weighted_sum / total_weight
    else:
        estimated_value = sum(prices) / len(prices)

    # Calculate value range (±10%)
    value_range_low = estimated_value * 0.90
    value_range_high = estimated_value * 1.10

    # Calculate confidence based on:
    # - Number of comparables (more = higher)
    # - Similarity scores (higher = higher)
    # - Price spread (lower = higher)
    num_comps = len(adjusted_comparables)
    avg_score = sum(c.get("similarity_score", 0) for c in adjusted_comparables) / num_comps

    price_stddev = 0.0
    if len(prices) > 1:
        mean_price = sum(prices) / len(prices)
        variance = sum((p - mean_price) ** 2 for p in prices) / len(prices)
        price_stddev = (variance**0.5) / mean_price if mean_price > 0 else 0

    # Confidence formula:
    # - Base from comparable count: min(1.0, num_comps / 6)
    # - Adjusted by average similarity score
    # - Reduced by price spread
    count_factor = min(1.0, num_comps / 6.0)
    score_factor = avg_score / 100.0
    spread_penalty = min(price_stddev, 0.3)  # Cap penalty at 30%

    confidence = count_factor * score_factor * (1.0 - spread_penalty)
    confidence = max(0.0, min(1.0, confidence))

    # Calculate price per sqm
    price_per_sqm = 0.0
    if subject.area_sqm and subject.area_sqm > 0:
        price_per_sqm = estimated_value / subject.area_sqm

    return CMAValuationResponse(
        estimated_value=round(estimated_value, 2),
        value_range_low=round(value_range_low, 2),
        value_range_high=round(value_range_high, 2),
        confidence_score=round(confidence, 2),
        price_per_sqm=round(price_per_sqm, 2),
        comparables_count=num_comps,  # type: ignore[call-arg]
        avg_adjusted_price=round(sum(prices) / len(prices), 2) if prices else 0.0,  # type: ignore[call-arg]
        median_adjusted_price=round(sorted(prices)[len(prices) // 2], 2) if prices else 0.0,  # type: ignore[call-arg]
        std_deviation=round(price_stddev, 2),  # type: ignore[call-arg]
    )


# ============================================================================
# Endpoints
# ============================================================================


@router.post(
    "/cma/comparables/{property_id}",
    response_model=list[CMAComparableResponse],
    tags=["CMA"],
)
async def find_comparables(
    property_id: str,
    max_distance_km: float = Query(default=5.0, ge=0.1, le=50.0),
    min_score: float = Query(default=50.0, ge=0, le=100),
    max_results: int = Query(default=6, ge=1, le=20),
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> list[CMAComparableResponse]:
    """
    Find comparable properties for a subject property.

    Uses multi-factor scoring (location, type, size, rooms, recency, amenities)
    to identify the most similar properties.

    Returns list of comparable properties with similarity scores.
    """
    # Fetch subject property from vector store
    store: ChromaPropertyStore = get_vector_store()
    docs = store.get_properties_by_ids([property_id])
    if not docs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Property {property_id} not found",
        )

    # Convert document to Property
    subject = _document_to_property(docs[0])

    # Get all properties for comparison
    all_docs = store.search_by_metadata(k=500)
    all_properties = [_document_to_property(d) for d in all_docs]
    collection = PropertyCollection(
        properties=all_properties, total_count=len(all_properties), source_type="vector_store"
    )  # type: ignore[call-arg]

    # Find comparables using multi-factor scoring
    selector = ComparableSelector(collection)
    scores = selector.find_comparables(
        subject=subject,
        max_distance_km=max_distance_km,
        min_score=min_score,
        max_results=max_results,
    )

    return [
        CMAComparableResponse(
            property_id=s.property_id,
            similarity_score=s.total_score,
            price=s.price,
            price_per_sqm=s.price_per_sqm,
            distance_km=s.distance_km,
            score_breakdown=s.score_breakdown,
        )
        for s in scores
    ]


@router.post(
    "/cma/generate",
    response_model=CMAReportResponse,
    tags=["CMA"],
)
async def generate_cma_report(
    request: CMAReportCreate,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> CMAReportResponse:
    """
    Generate a Comparative Market Analysis (CMA) report.

    This endpoint:
    1. Fetches the subject property
    2. Finds comparable properties using multi-factor scoring
    3. Calculates adjustments for differences
    4. Produces a final valuation estimate

    The report is saved and can be retrieved later or exported as PDF.
    """
    try:
        # Fetch subject property from vector store
        store: ChromaPropertyStore = get_vector_store()
        docs = store.get_properties_by_ids([request.subject_property_id])
        if not docs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Subject property {request.subject_property_id} not found",
            )

        subject = _document_to_property(docs[0])

        # Get all properties for comparison
        all_docs = store.search_by_metadata(k=500)
        all_properties = [_document_to_property(d) for d in all_docs]
        collection = PropertyCollection(
            properties=all_properties, total_count=len(all_properties), source_type="vector_store"
        )  # type: ignore[call-arg]

        # Find comparables
        selector = ComparableSelector(collection)
        scores = selector.find_comparables(
            subject=subject,
            max_distance_km=request.max_distance_km,
            min_score=50.0,
            max_results=request.max_comparables,
        )

        # Filter by specific IDs if provided
        if request.comparable_ids:
            scores = [s for s in scores if s.property_id in request.comparable_ids]

        # Ensure minimum comparables
        if len(scores) < request.min_comparables:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Found only {len(scores)} comparables, need at least {request.min_comparables}",
            )

        # Calculate adjustments for each comparable
        from analytics.cma_adjustments import CMAAdjustmentCalculator

        calculator = CMAAdjustmentCalculator()
        adjusted_comparables = []

        for score in scores:
            comp = next((p for p in all_properties if p.id == score.property_id), None)
            if not comp:
                continue

            adjustments = calculator.calculate_adjustments(subject, comp, score.price)
            adjusted = calculator.apply_adjustments(score.price, adjustments)
            adjusted.property_id = score.property_id

            adjusted_comparables.append(
                {
                    "property_id": score.property_id,
                    "similarity_score": score.total_score,
                    "adjustments": [a.to_dict() for a in adjustments],
                    "adjusted_price": adjusted.adjusted_price,
                }
            )

        # Calculate final valuation
        valuation = _calculate_valuation(subject, adjusted_comparables)

        # Store report
        repo = CMAReportRepository(session)
        report = await repo.create(
            user_id=user.id,
            subject_property_id=request.subject_property_id,
            subject_data=_property_to_dict(subject),
            comparables=adjusted_comparables,
            valuation=valuation.model_dump(),
            status="completed",
        )

        subject_dict = _property_to_dict(subject)
        return CMAReportResponse(
            id=report.id,
            user_id=report.user_id,
            status=report.status,
            subject_property_id=subject_dict.get("id", ""),  # type: ignore[call-arg]
            subject_address=subject_dict.get("address"),  # type: ignore[call-arg]
            subject_city=subject_dict.get("city", ""),  # type: ignore[call-arg]
            subject_district=subject_dict.get("district"),  # type: ignore[call-arg]
            subject_price=subject_dict.get("price"),  # type: ignore[call-arg]
            subject_area_sqm=subject_dict.get("area_sqm"),  # type: ignore[call-arg]
            subject_rooms=subject_dict.get("rooms"),  # type: ignore[call-arg]
            subject_year_built=subject_dict.get("year_built"),  # type: ignore[call-arg]
            subject_property_type=subject_dict.get("property_type", "apartment"),  # type: ignore[call-arg]
            subject_energy_rating=subject_dict.get("energy_rating"),  # type: ignore[call-arg]
            subject_amenities=subject_dict.get("amenities", {}),  # type: ignore[call-arg]
            comparables=[CMAComparableResponse(**c) for c in adjusted_comparables],
            valuation=valuation,
            created_at=report.created_at,
            expires_at=report.expires_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("CMA report generation failed: %s", sanitize_for_log(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Report generation failed: {str(e)}",
        ) from e


@router.get(
    "/cma/{report_id}",
    response_model=CMAReportResponse,
    tags=["CMA"],
)
async def get_cma_report(
    report_id: str,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> CMAReportResponse:
    """
    Retrieve a saved CMA report by ID.

    Only the report owner can access the report.
    """
    repo = CMAReportRepository(session)
    report = await repo.get_by_id(report_id, user.id)

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CMA report not found",
        )

    subject_data = report.subject_data if isinstance(report.subject_data, dict) else {}
    return CMAReportResponse(
        id=report.id,
        user_id=report.user_id,
        status=report.status,
        subject_property_id=subject_data.get("id", ""),  # type: ignore[call-arg]
        subject_address=subject_data.get("address"),  # type: ignore[call-arg]
        subject_city=subject_data.get("city", ""),  # type: ignore[call-arg]
        subject_district=subject_data.get("district"),  # type: ignore[call-arg]
        subject_price=subject_data.get("price"),  # type: ignore[call-arg]
        subject_area_sqm=subject_data.get("area_sqm"),  # type: ignore[call-arg]
        subject_rooms=subject_data.get("rooms"),  # type: ignore[call-arg]
        subject_year_built=subject_data.get("year_built"),  # type: ignore[call-arg]
        subject_property_type=subject_data.get("property_type", "apartment"),  # type: ignore[call-arg]
        subject_energy_rating=subject_data.get("energy_rating"),  # type: ignore[call-arg]
        subject_amenities=subject_data.get("amenities", {}),  # type: ignore[call-arg]
        comparables=[CMAComparableResponse(**c) for c in report.comparables],
        valuation=CMAValuationResponse(**report.valuation),
        market_trend=subject_data.get("market_context", {}).get("trend")
        if isinstance(subject_data.get("market_context"), dict)
        else None,  # type: ignore[call-arg]
        market_avg_price_per_sqm=subject_data.get("market_context", {}).get("avg_price_per_sqm")
        if isinstance(subject_data.get("market_context"), dict)
        else None,  # type: ignore[call-arg]
        market_inventory_days=subject_data.get("market_context", {}).get("inventory_days")
        if isinstance(subject_data.get("market_context"), dict)
        else None,  # type: ignore[call-arg]
        created_at=report.created_at,
        expires_at=report.expires_at,
    )


@router.get(
    "/cma/{report_id}/pdf",
    tags=["CMA"],
)
async def download_cma_pdf(
    report_id: str,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """
    Download CMA report as PDF.

    Generates a professional PDF report with:
    - Executive summary
    - Subject property details
    - Comparables grid
    - Adjustments breakdown
    - Final valuation
    """
    repo = CMAReportRepository(session)
    report = await repo.get_by_id(report_id, user.id)

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CMA report not found",
        )

    try:
        # Import PDF generator (to be created)
        from utils.cma_report_generator import CMAReportGenerator

        generator = CMAReportGenerator()
        pdf_buffer = generator.generate(
            subject_data=report.subject_data,
            comparables=report.comparables,
            valuation=report.valuation,
            market_context=report.market_context,
        )

        # Generate filename
        address = report.subject_data.get("street", "property")
        safe_address = "".join(c if c.isalnum() or c in " -_" else "_" for c in address)
        filename = f"CMA_Report_{safe_address}_{report_id[:8]}.pdf"

        return StreamingResponse(
            BytesIO(pdf_buffer),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="PDF generation not yet implemented",
        ) from None
    except Exception as e:
        logger.error("PDF generation failed: %s", sanitize_for_log(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PDF generation failed: {str(e)}",
        ) from e


@router.get(
    "/cma",
    response_model=CMAReportListResponse,
    tags=["CMA"],
)
async def list_cma_reports(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> CMAReportListResponse:
    """
    List user's CMA reports.

    Supports pagination and filtering by status.
    """
    repo = CMAReportRepository(session)

    offset = (page - 1) * page_size
    reports = await repo.get_by_user(
        user_id=user.id,
        status=status_filter,
        include_expired=False,
        limit=page_size,
        offset=offset,
    )

    total = await repo.count_by_user(
        user_id=user.id,
        status=status_filter,
        include_expired=False,
    )

    return CMAReportListResponse(
        items=[
            CMAReportResponse(
                id=r.id,
                user_id=r.user_id,
                status=r.status,
                subject_property_id=r.subject_data.get("id", "")
                if isinstance(r.subject_data, dict)
                else "",  # type: ignore[call-arg]
                subject_address=r.subject_data.get("address")
                if isinstance(r.subject_data, dict)
                else None,  # type: ignore[call-arg]
                subject_city=r.subject_data.get("city", "")
                if isinstance(r.subject_data, dict)
                else "",  # type: ignore[call-arg]
                subject_district=r.subject_data.get("district")
                if isinstance(r.subject_data, dict)
                else None,  # type: ignore[call-arg]
                subject_price=r.subject_data.get("price")
                if isinstance(r.subject_data, dict)
                else None,  # type: ignore[call-arg]
                subject_area_sqm=r.subject_data.get("area_sqm")
                if isinstance(r.subject_data, dict)
                else None,  # type: ignore[call-arg]
                subject_rooms=r.subject_data.get("rooms")
                if isinstance(r.subject_data, dict)
                else None,  # type: ignore[call-arg]
                subject_year_built=r.subject_data.get("year_built")
                if isinstance(r.subject_data, dict)
                else None,  # type: ignore[call-arg]
                subject_property_type=r.subject_data.get("property_type", "apartment")
                if isinstance(r.subject_data, dict)
                else "apartment",  # type: ignore[call-arg]
                subject_energy_rating=r.subject_data.get("energy_rating")
                if isinstance(r.subject_data, dict)
                else None,  # type: ignore[call-arg]
                subject_amenities=r.subject_data.get("amenities", {})
                if isinstance(r.subject_data, dict)
                else {},  # type: ignore[call-arg]
                comparables=[CMAComparableResponse(**c) for c in r.comparables],
                valuation=CMAValuationResponse(**r.valuation),
                market_trend=r.subject_data.get("market_context", {}).get("trend")
                if isinstance(r.subject_data, dict)
                and isinstance(r.subject_data.get("market_context"), dict)
                else None,  # type: ignore[call-arg]
                market_avg_price_per_sqm=r.subject_data.get("market_context", {}).get(
                    "avg_price_per_sqm"
                )
                if isinstance(r.subject_data, dict)
                and isinstance(r.subject_data.get("market_context"), dict)
                else None,  # type: ignore[call-arg]
                market_inventory_days=r.subject_data.get("market_context", {}).get("inventory_days")
                if isinstance(r.subject_data, dict)
                and isinstance(r.subject_data.get("market_context"), dict)
                else None,  # type: ignore[call-arg]
                created_at=r.created_at,
                expires_at=r.expires_at,
            )
            for r in reports
        ],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if page_size else 0,
    )


@router.delete(
    "/cma/{report_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["CMA"],
)
async def delete_cma_report(
    report_id: str,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    """
    Delete a CMA report.

    Only the report owner can delete the report.
    """
    repo = CMAReportRepository(session)
    report = await repo.get_by_id(report_id, user.id)

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CMA report not found",
        )

    await repo.delete(report)
