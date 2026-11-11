"""One property, by its id.

The search answers with listings, the card shows them, and until now that was
the end of the road: the interface had no page for a single property. The
marketing copy promised one - "an AI neighbourhood one-liner on every property
page" - and there was no route to deliver it on.

This router is that page's data. It answers with the listing itself, read from
the vector store where the properties actually live, and with the comparables
and the price history that the page shows next to it.

The page is public: a visitor who clicks a listing on the search page is
nobody until they sign in, so the data it needs is readable without a session.
"""

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_vector_store
from data.schemas import normalize_property_metadata
from db.analytics_repos import PriceSnapshotRepository
from db.database import get_db

router = APIRouter(prefix="/properties", tags=["Properties"])


def _document_to_property(doc: Any) -> dict[str, Any]:
    """The listing as the interface expects it.

    The vector store writes the coordinates as ``lat``/``lon`` and the schema
    names them ``latitude``/``longitude``; the normalizer bridges the two.
    Everything the card already reads is passed through, so the detail page
    and the card speak the same language about the same listing.
    """
    metadata = normalize_property_metadata(doc.metadata or {})
    return {
        "id": metadata.get("id"),
        "title": metadata.get("title"),
        "description": metadata.get("description") or doc.page_content,
        "city": metadata.get("city"),
        "country": metadata.get("country"),
        "region": metadata.get("region"),
        "district": metadata.get("district"),
        "neighborhood": metadata.get("neighborhood"),
        "address": metadata.get("address"),
        "latitude": metadata.get("latitude"),
        "longitude": metadata.get("longitude"),
        "property_type": metadata.get("property_type"),
        "listing_type": metadata.get("listing_type"),
        "rooms": metadata.get("rooms"),
        "bathrooms": metadata.get("bathrooms"),
        "area_sqm": metadata.get("area_sqm"),
        "floor": metadata.get("floor"),
        "total_floors": metadata.get("total_floors"),
        "year_built": metadata.get("year_built"),
        "energy_rating": metadata.get("energy_cert"),
        "price": metadata.get("price"),
        "currency": metadata.get("currency"),
        "price_per_sqm": metadata.get("price_per_sqm"),
        "price_delta": metadata.get("price_delta"),
        "deposit": metadata.get("deposit"),
        "negotiation_rate": metadata.get("negotiation_rate"),
        "has_parking": bool(metadata.get("has_parking", False)),
        "has_garden": bool(metadata.get("has_garden", False)),
        "has_pool": bool(metadata.get("has_pool", False)),
        "has_garage": bool(metadata.get("has_garage", False)),
        "has_bike_room": bool(metadata.get("has_bike_room", False)),
        "has_elevator": bool(metadata.get("has_elevator", False)),
        "images": metadata.get("images") or [],
        "source_url": metadata.get("source_url") or "",
        "source_platform": metadata.get("source_platform") or "",
        "scraped_at": metadata.get("scraped_at"),
    }


@router.get(
    "/{property_id}",
    summary="One property",
    description=(
        "The listing itself, read from the catalogue the search answers with. "
        "This is the data of the property page."
    ),
)
async def get_property(
    property_id: str,
    store: Optional[Any] = Depends(get_vector_store),
) -> dict[str, Any]:
    """The listing, or a refusal when the catalogue does not hold it."""
    cleaned = property_id.strip()
    if not cleaned:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="property_id is required",
        )
    if not store:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Vector store unavailable",
        )

    docs = store.get_properties_by_ids([cleaned])
    if not docs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found",
        )

    return _document_to_property(docs[0])


@router.get(
    "/{property_id}/price-history",
    summary="The price history of one property",
    description="The recorded price points of the listing, newest first.",
)
async def get_property_price_history(
    property_id: str,
    limit: int = Query(default=100, ge=1, le=1000),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """The price history, or an empty series when none was recorded."""
    cleaned = property_id.strip()
    if not cleaned:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="property_id is required",
        )

    repo = PriceSnapshotRepository(session)
    snapshots = await repo.get_by_property(cleaned, limit=limit)
    total = await repo.count_for_property(cleaned)

    points = [
        {
            "price": snapshot.price,
            "price_per_sqm": snapshot.price_per_sqm,
            "currency": snapshot.currency,
            "source": snapshot.source,
            "recorded_at": (snapshot.recorded_at.isoformat() if snapshot.recorded_at else None),
        }
        for snapshot in snapshots
    ]

    return {
        "property_id": cleaned,
        "snapshots": points,
        "total": total,
    }


@router.get(
    "/{property_id}/related",
    summary="Listings like this one",
    description=(
        "The other listings in the same city and of the same type - the "
        "comparables the page shows next to this one."
    ),
)
async def get_related_properties(
    property_id: str,
    limit: int = Query(default=6, ge=1, le=24),
    store: Optional[Any] = Depends(get_vector_store),
) -> dict[str, Any]:
    """The comparables, or an empty list when the catalogue holds none."""
    cleaned = property_id.strip()
    if not cleaned:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="property_id is required",
        )
    if not store:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Vector store unavailable",
        )

    docs = store.get_properties_by_ids([cleaned])
    if not docs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found",
        )

    subject = normalize_property_metadata(docs[0].metadata or {})
    city = subject.get("city")
    property_type = subject.get("property_type")

    if not city:
        return {"properties": [], "count": 0}

    try:
        found = store.search_by_metadata(city=city, k=max(limit * 3, 20))
    except Exception:
        return {"properties": [], "count": 0}

    related: list[dict[str, Any]] = []
    for doc in found or []:
        metadata = normalize_property_metadata(doc.metadata or {})
        if metadata.get("id") == cleaned:
            continue
        if property_type and metadata.get("property_type") != property_type:
            continue
        related.append(_document_to_property(doc))
        if len(related) >= limit:
            break

    return {"properties": related, "count": len(related)}
