"""The place pages: what the official register holds for a city or a district.

WHY THESE ENDPOINTS EXIST

The pages that could carry real content did not exist. A city page that says
what a square metre costs there, on how many registered sales and over which
period, is a page a crawler can read and a reader can check - and the register
holds the numbers for the five cities the site knows.

The register knows streets, not districts, so a district's figures are the
figures of the sales registered on the streets that district stands on. The
endpoints say which streets those are, so the page never presents a district's
number without naming where it came from.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.models import (
    PlaceCatalogueResponse,
    PlaceDistrictResponse,
    PlaceFiguresResponse,
    PlaceSummaryResponse,
    ValuationComparable,
)
from data.places import (
    find_district_by_slug,
    find_place_by_slug,
    place_slug,
)
from db.database import get_db

router = APIRouter(prefix="/places", tags=["Places"])


def _summary(place, districts) -> PlaceSummaryResponse:
    return PlaceSummaryResponse(
        name=place.name,
        slug=place_slug(place.name),
        register_city=place.register_city,
        districts=[
            PlaceDistrictResponse(name=district.name, slug=place_slug(district.name))
            for district in districts
        ],
    )


@router.get(
    "",
    response_model=PlaceCatalogueResponse,
    summary="The places the site knows",
    description=("The cities the register covers, with the districts it covers of each."),
)
async def place_catalogue(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> PlaceCatalogueResponse:
    """The catalogue of places, so a page can link to the others.

    Only the places the register holds sales for are listed: a city or a
    district it holds nothing for has no page, and a link or a sitemap entry
    that names it would lead to nothing.
    """
    from agents.services.valuation import RcnValuationProvider

    covered = await RcnValuationProvider(session).covered_places()
    return PlaceCatalogueResponse(
        places=[_summary(place, districts) for place, districts in covered]
    )


@router.get(
    "/{city}",
    response_model=PlaceFiguresResponse,
    summary="What the register holds for a city",
    description=(
        "The price a square metre costs in a city, the registered sales that "
        "figure is measured on, the period those sales cover and the sales "
        "themselves."
    ),
)
async def city_figures(
    city: str,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> PlaceFiguresResponse:
    """What the register says about a city."""
    return await _figures(city, "", session)


@router.get(
    "/{city}/{district}",
    response_model=PlaceFiguresResponse,
    summary="What the register holds for a district",
    description=(
        "The price a square metre costs in a district, measured on the sales "
        "registered on the streets that district stands on."
    ),
)
async def district_figures(
    city: str,
    district: str,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> PlaceFiguresResponse:
    """What the register says about a district of a city."""
    return await _figures(city, district, session)


async def _figures(
    city: str,
    district: str,
    session: AsyncSession,
) -> PlaceFiguresResponse:
    """The figures of a place, read from the register."""
    from agents.services.valuation import RcnValuationProvider

    place = find_place_by_slug(city)
    if place is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"The site knows no city called {city}.",
        )

    district_entry = None
    if district:
        district_entry = find_district_by_slug(place, district)
        if district_entry is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{place.name} has no district called {district}.",
            )

    outcome = await RcnValuationProvider(session).place_outcome(
        place.name,
        district_entry.name if district_entry else "",
    )
    if not outcome.has_figures:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"The official register holds no registered sale for {outcome.comparison_area}."
            ),
        )

    return PlaceFiguresResponse(
        place=outcome.place,
        slug=place_slug(place.name),
        district=outcome.district,
        district_slug=place_slug(district_entry.name) if district_entry else "",
        median_price_per_sqm=outcome.median_price_per_sqm,
        first_quartile_price_per_sqm=outcome.first_quartile_price_per_sqm,
        third_quartile_price_per_sqm=outcome.third_quartile_price_per_sqm,
        currency=outcome.currency,
        source=outcome.source,
        confidence=outcome.confidence,
        sample_size=outcome.sample_size,
        registered_count=outcome.registered_count,
        comparison_area=outcome.comparison_area,
        period_start=outcome.period_start,
        period_end=outcome.period_end,
        notes=outcome.notes,
        comparables=[ValuationComparable(**comparable) for comparable in outcome.comparables],
        districts=[
            PlaceDistrictResponse(name=name, slug=place_slug(name)) for name in outcome.districts
        ],
    )
