from typing import Annotated, List, Optional
import statistics

from fastapi import APIRouter, Depends, HTTPException, status
from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel, Field

from api.dependencies import (
    get_crm_connector,
    get_data_enrichment_service,
    get_legal_check_service,
    get_llm,
    get_valuation_provider,
    get_vector_store,
)
from api.models import (
    CRMContactRequest,
    CRMContactResponse,
    ComparePropertiesRequest,
    ComparePropertiesResponse,
    CompareSummary,
    ComparedProperty,
    CommuteRankingRequest,
    CommuteRankingResponse,
    CommuteTimeRequest,
    CommuteTimeResponse,
    CommuteTimeResult,
    DataEnrichmentRequest,
    DataEnrichmentResponse,
    LegalCheckRequest,
    LegalCheckResponse,
    LocationAnalysisRequest,
    LocationAnalysisResponse,
    NegotiationRequest,
    NegotiationResponse,
    NegotiationPriceBand,
    NegotiationPropertyInfo,
    NeighborhoodQualityResponse,
    PriceAnalysisRequest,
    PriceAnalysisResponse,
    ValuationRequest,
    ValuationResponse,
)
from tools.property_tools import (
    AdvancedInvestmentInput,
    AdvancedInvestmentResult,
    AdvancedInvestmentTool,
    InvestmentCalculatorTool,
    InvestmentAnalysisInput,
    InvestmentAnalysisResult,
    MortgageCalculatorTool,
    MortgageInput,
    MortgageResult,
    NeighborhoodQualityIndexTool,
    NeighborhoodQualityInput,
    RentVsBuyCalculatorTool,
    RentVsBuyInput,
    RentVsBuyResult,
    TCOComparisonInput,
    TCOComparisonResult,
    TCOComparisonTool,
    TCOCalculatorTool,
    TCOInput,
    TCOResult,
    create_property_tools,
)
from data.location_defaults import get_location_defaults, get_available_locations
from tools.negotiation_tool import NegotiationTool
from tools.portfolio_tools import (
    PortfolioAnalysisInput,
    PortfolioAnalysisResult,
    PortfolioAnalyzerTool,
)
from tools.listing_generator_tools import (
    PropertyDescriptionGeneratorTool,
    HeadlineGeneratorTool,
    SocialMediaContentGeneratorTool,
)
from vector_store.chroma_store import ChromaPropertyStore

router = APIRouter(tags=["Tools"])


class ToolInfo(BaseModel):
    """Information about an available tool."""

    name: str
    description: str


@router.get("/tools", response_model=List[ToolInfo], tags=["Tools"])
async def list_tools():
    """List available tools."""
    tools = create_property_tools()
    items = [ToolInfo(name=tool.name, description=tool.description) for tool in tools]
    items.extend(
        [
            ToolInfo(
                name="valuation",
                description="Estimate property value from listing metadata (CE stub; may be disabled).",
            ),
            ToolInfo(
                name="legal_check",
                description="Basic contract text risk check (CE stub; may be disabled).",
            ),
            ToolInfo(
                name="enrich_address",
                description="Address enrichment (CE stub; gated by DATA_ENRICHMENT_ENABLED).",
            ),
            ToolInfo(
                name="crm_sync_contact",
                description="CRM contact sync via webhook (CE stub; gated by CRM_WEBHOOK_URL).",
            ),
        ]
    )
    return items


@router.post("/tools/mortgage-calculator", response_model=MortgageResult, tags=["Tools"])
async def calculate_mortgage(input_data: MortgageInput):
    """
    Calculate mortgage payments.
    """
    try:
        return MortgageCalculatorTool.calculate(
            property_price=input_data.property_price,
            down_payment_percent=input_data.down_payment_percent,
            interest_rate=input_data.interest_rate,
            loan_years=input_data.loan_years,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Calculation failed: {str(e)}",
        ) from e


@router.post("/tools/tco-calculator", response_model=TCOResult, tags=["Tools"])
async def calculate_tco(input_data: TCOInput):
    """
    Calculate Total Cost of Ownership for a property.
    Includes mortgage, property taxes, insurance, HOA fees, utilities, maintenance, and parking.
    """
    try:
        return TCOCalculatorTool.calculate(
            property_price=input_data.property_price,
            down_payment_percent=input_data.down_payment_percent,
            interest_rate=input_data.interest_rate,
            loan_years=input_data.loan_years,
            monthly_hoa=input_data.monthly_hoa,
            annual_property_tax=input_data.annual_property_tax,
            annual_insurance=input_data.annual_insurance,
            monthly_utilities=input_data.monthly_utilities,
            monthly_internet=input_data.monthly_internet,
            monthly_parking=input_data.monthly_parking,
            maintenance_percent=input_data.maintenance_percent,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Calculation failed: {str(e)}",
        ) from e


# Task #52: TCO Comparison Endpoint
@router.post("/tools/tco-comparison", response_model=TCOComparisonResult, tags=["Tools"])
async def compare_tco(input_data: TCOComparisonInput):
    """
    Compare Total Cost of Ownership between two property scenarios.

    Provides:
    - Side-by-side enhanced TCO analysis with projections
    - Cost difference calculations (monthly and total)
    - Break-even analysis (when one scenario becomes better)
    - Trade-off analysis with pros/cons
    - Priority-weighted recommendation based on user preferences
    """
    try:
        return TCOComparisonTool.calculate(input_data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Comparison failed: {str(e)}",
        ) from e


# Task #52: Location Defaults Endpoint
class LocationDefaultsResponse(BaseModel):
    """Response model for location defaults."""

    country: str
    region: str
    property_tax_rate: float
    avg_insurance_rate: float
    avg_utilities_per_sqm: float
    avg_internet: float
    avg_parking: float
    currency: str = "USD"


class AvailableLocationsResponse(BaseModel):
    """Response model for available locations."""

    locations: dict[str, list[str]]


@router.get(
    "/tools/tco-location-defaults",
    response_model=LocationDefaultsResponse,
    tags=["Tools"],
)
async def get_tco_location_defaults(country: str, region: str | None = None):
    """
    Get location-based default cost estimates for TCO Calculator.

    Returns reasonable default values for:
    - Property tax rates (annual % of property value)
    - Insurance rates (annual % of property value)
    - Utilities per sqm (monthly)
    - Internet costs (monthly)
    - Parking costs (monthly)

    Supports EU (DE, ES, GB, FR, IT, NL) and USA regions.
    """
    try:
        defaults = get_location_defaults(country, region)
        return LocationDefaultsResponse(
            country=country.upper(),
            region=region.lower().replace(" ", "_").replace("-", "_") if region else "default",
            property_tax_rate=defaults["property_tax_rate"],
            avg_insurance_rate=defaults["avg_insurance_rate"],
            avg_utilities_per_sqm=defaults["avg_utilities_per_sqm"],
            avg_internet=defaults["avg_internet"],
            avg_parking=defaults["avg_parking"],
            currency=defaults.get("currency", "USD"),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get location defaults: {str(e)}",
        ) from e


@router.get(
    "/tools/tco-available-locations",
    response_model=AvailableLocationsResponse,
    tags=["Tools"],
)
async def list_tco_available_locations():
    """
    List all available locations with TCO default values.

    Returns a dictionary mapping country codes to lists of available regions.
    """
    try:
        return AvailableLocationsResponse(locations=get_available_locations())
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get available locations: {str(e)}",
        ) from e


@router.post("/tools/investment-analysis", response_model=InvestmentAnalysisResult, tags=["Tools"])
async def calculate_investment_analysis(input_data: InvestmentAnalysisInput):
    """
    Calculate investment property metrics including ROI, cap rate, cash flow, and rental yield.
    """
    try:
        return InvestmentCalculatorTool.calculate(
            property_price=input_data.property_price,
            monthly_rent=input_data.monthly_rent,
            down_payment_percent=input_data.down_payment_percent,
            closing_costs=input_data.closing_costs,
            renovation_costs=input_data.renovation_costs,
            interest_rate=input_data.interest_rate,
            loan_years=input_data.loan_years,
            property_tax_monthly=input_data.property_tax_monthly,
            insurance_monthly=input_data.insurance_monthly,
            hoa_monthly=input_data.hoa_monthly,
            maintenance_percent=input_data.maintenance_percent,
            vacancy_rate=input_data.vacancy_rate,
            management_percent=input_data.management_percent,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Calculation failed: {str(e)}",
        ) from e


# Task #39: Advanced Investment Analytics
@router.post(
    "/tools/advanced-investment-analysis",
    response_model=AdvancedInvestmentResult,
    tags=["Tools"],
)
async def calculate_advanced_investment(input_data: AdvancedInvestmentInput):
    """
    Advanced investment analysis with multi-year projections, tax implications,
    appreciation scenarios, and risk assessment.
    """
    try:
        return AdvancedInvestmentTool.calculate(
            property_price=input_data.property_price,
            monthly_rent=input_data.monthly_rent,
            down_payment_percent=input_data.down_payment_percent,
            interest_rate=input_data.interest_rate,
            loan_years=input_data.loan_years,
            property_tax_monthly=input_data.property_tax_monthly,
            insurance_monthly=input_data.insurance_monthly,
            hoa_monthly=input_data.hoa_monthly,
            maintenance_percent=input_data.maintenance_percent,
            vacancy_rate=input_data.vacancy_rate,
            management_percent=input_data.management_percent,
            projection_years=input_data.projection_years,
            appreciation_rate=input_data.appreciation_rate,
            rent_growth_rate=input_data.rent_growth_rate,
            marginal_tax_rate=input_data.marginal_tax_rate,
            land_value_ratio=input_data.land_value_ratio,
            market_volatility=input_data.market_volatility,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Advanced analysis failed: {str(e)}",
        ) from e


# Task #39: Portfolio Analysis
@router.post(
    "/tools/portfolio-analysis",
    response_model=PortfolioAnalysisResult,
    tags=["Tools"],
)
async def analyze_portfolio(input_data: PortfolioAnalysisInput):
    """
    Analyze a portfolio of investment properties including aggregate metrics,
    diversification scores, and risk assessment.
    """
    try:
        return PortfolioAnalyzerTool.calculate(
            properties=input_data.properties,
            market_volatility_by_city=input_data.market_volatility_by_city,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Portfolio analysis failed: {str(e)}",
        ) from e


# Task #42: Rent vs Buy Calculator
@router.post(
    "/tools/rent-vs-buy",
    response_model=RentVsBuyResult,
    tags=["Tools"],
)
async def calculate_rent_vs_buy(input_data: RentVsBuyInput):
    """
    Compare renting vs buying a property over time.

    Calculates:
    - Monthly payment comparison
    - Total cost over time
    - Break-even point (when buying becomes cheaper)
    - Opportunity cost of down payment
    - Tax benefits of ownership
    - Property appreciation impact
    """
    try:
        return RentVsBuyCalculatorTool.calculate(
            property_price=input_data.property_price,
            monthly_rent=input_data.monthly_rent,
            down_payment_percent=input_data.down_payment_percent,
            interest_rate=input_data.interest_rate,
            loan_years=input_data.loan_years,
            annual_property_tax=input_data.annual_property_tax,
            annual_insurance=input_data.annual_insurance,
            monthly_hoa=input_data.monthly_hoa,
            maintenance_percent=input_data.maintenance_percent,
            appreciation_rate=input_data.appreciation_rate,
            rent_increase_rate=input_data.rent_increase_rate,
            investment_return_rate=input_data.investment_return_rate,
            marginal_tax_rate=input_data.marginal_tax_rate,
            projection_years=input_data.projection_years,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Rent vs Buy calculation failed: {str(e)}",
        ) from e


@router.post(
    "/tools/neighborhood-quality",
    response_model=NeighborhoodQualityResponse,
    tags=["Tools"],
)
async def neighborhood_quality(input_data: NeighborhoodQualityInput):
    """
    Calculate enhanced neighborhood quality index.

    Returns scores for 8 factors:
    - Core: Safety, Schools, Amenities, Walkability, Green Space
    - New: Air Quality, Noise Level, Public Transport

    Includes city comparison and nearby POIs for map visualization.
    """
    try:
        result = NeighborhoodQualityIndexTool.calculate(
            property_id=input_data.property_id,
            latitude=input_data.latitude,
            longitude=input_data.longitude,
            city=input_data.city,
            neighborhood=input_data.neighborhood,
            custom_weights=input_data.custom_weights,
            compare_to_city_average=input_data.compare_to_city_average,
            include_pois=input_data.include_pois,
        )

        # Convert tool result to response model
        return NeighborhoodQualityResponse(
            property_id=result.property_id,
            overall_score=result.overall_score,
            safety_score=result.safety_score,
            schools_score=result.schools_score,
            amenities_score=result.amenities_score,
            walkability_score=result.walkability_score,
            green_space_score=result.green_space_score,
            air_quality_score=result.air_quality_score,
            noise_level_score=result.noise_level_score,
            public_transport_score=result.public_transport_score,
            score_breakdown=result.score_breakdown,
            factor_details=result.factor_details,
            city_comparison=result.city_comparison,
            nearby_pois=result.nearby_pois,
            data_sources=result.data_sources,
            data_freshness=result.data_freshness,
            latitude=result.latitude,
            longitude=result.longitude,
            city=result.city,
            neighborhood=result.neighborhood,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Neighborhood quality calculation failed: {str(e)}",
        ) from e


@router.post(
    "/tools/compare-properties",
    response_model=ComparePropertiesResponse,
    tags=["Tools"],
)
async def compare_properties(
    request: ComparePropertiesRequest,
    store: Annotated[Optional[ChromaPropertyStore], Depends(get_vector_store)],
):
    if not store:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Vector store unavailable",
        )

    property_ids = [pid.strip() for pid in request.property_ids if pid and pid.strip()]
    if not property_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one property_id is required",
        )

    docs = store.get_properties_by_ids(property_ids)
    if not docs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No properties found for provided IDs",
        )

    properties = []
    prices: List[float] = []
    for doc in docs:
        md = doc.metadata or {}
        item = ComparedProperty(
            id=str(md.get("id")) if md.get("id") is not None else None,
            price=_to_float(md.get("price")),
            price_per_sqm=_to_float(md.get("price_per_sqm")),
            city=md.get("city"),
            rooms=_to_float(md.get("rooms")),
            bathrooms=_to_float(md.get("bathrooms")),
            area_sqm=_to_float(md.get("area_sqm")),
            year_built=_to_int(md.get("year_built")),
            property_type=md.get("property_type"),
        )
        if item.price is not None:
            prices.append(item.price)
        properties.append(item)

    summary = CompareSummary(
        count=len(properties),
        min_price=min(prices) if prices else None,
        max_price=max(prices) if prices else None,
        price_difference=(max(prices) - min(prices)) if len(prices) >= 2 else None,
    )

    return ComparePropertiesResponse(properties=properties, summary=summary)


@router.post("/tools/price-analysis", response_model=PriceAnalysisResponse, tags=["Tools"])
async def price_analysis(
    request: PriceAnalysisRequest,
    store: Annotated[Optional[ChromaPropertyStore], Depends(get_vector_store)],
):
    if not store:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Vector store unavailable",
        )

    query = request.query.strip()
    if not query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="query is required",
        )

    results = store.search(query, k=20)
    if not results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No properties found for analysis",
        )

    docs = [doc for doc, _score in results]
    prices: List[float] = []
    sqm_prices: List[float] = []
    distribution: dict[str, int] = {}

    for doc in docs:
        md = doc.metadata or {}
        raw_price = _to_float(md.get("price"))
        if raw_price is not None:
            prices.append(raw_price)
        raw_ppsqm = _to_float(md.get("price_per_sqm"))
        if raw_ppsqm is not None:
            sqm_prices.append(raw_ppsqm)

        ptype = md.get("property_type") or "Unknown"
        distribution[str(ptype)] = distribution.get(str(ptype), 0) + 1

    return PriceAnalysisResponse(
        query=query,
        count=len(docs),
        average_price=statistics.mean(prices) if prices else None,
        median_price=statistics.median(prices) if prices else None,
        min_price=min(prices) if prices else None,
        max_price=max(prices) if prices else None,
        average_price_per_sqm=statistics.mean(sqm_prices) if sqm_prices else None,
        median_price_per_sqm=statistics.median(sqm_prices) if sqm_prices else None,
        distribution_by_type=distribution,
    )


@router.post("/tools/location-analysis", response_model=LocationAnalysisResponse, tags=["Tools"])
async def location_analysis(
    request: LocationAnalysisRequest,
    store: Annotated[Optional[ChromaPropertyStore], Depends(get_vector_store)],
):
    if not store:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Vector store unavailable",
        )

    property_id = request.property_id.strip()
    if not property_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="property_id is required",
        )

    docs = store.get_properties_by_ids([property_id])
    if not docs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found",
        )

    md = docs[0].metadata or {}
    return LocationAnalysisResponse(
        property_id=property_id,
        city=md.get("city"),
        neighborhood=md.get("neighborhood"),
        lat=_to_float(md.get("lat")),
        lon=_to_float(md.get("lon")),
    )


@router.post("/tools/valuation", response_model=ValuationResponse, tags=["Tools"])
async def valuation(
    request: ValuationRequest,
    store: Annotated[Optional[ChromaPropertyStore], Depends(get_vector_store)],
    provider=Depends(get_valuation_provider),
):
    if not store:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Vector store unavailable",
        )
    if provider is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Valuation disabled",
        )
    pid = request.property_id.strip()
    if not pid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="property_id is required",
        )
    docs = store.get_properties_by_ids([pid])
    if not docs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found",
        )
    md = docs[0].metadata or {}
    area = md.get("area_sqm")
    price_per_sqm = md.get("price_per_sqm")
    value = provider.estimate_value({"area": area, "price_per_sqm": price_per_sqm})
    return ValuationResponse(property_id=pid, estimated_value=value)


@router.post("/tools/legal-check", response_model=LegalCheckResponse, tags=["Tools"])
async def legal_check(
    request: LegalCheckRequest,
    service=Depends(get_legal_check_service),
):
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Legal check disabled",
        )
    text = request.text.strip()
    if not text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="text is required",
        )
    result = service.analyze_contract(text)
    return LegalCheckResponse(
        risks=result.get("risks", []),
        score=float(result.get("score", 0.0)),
    )


@router.post("/tools/enrich-address", response_model=DataEnrichmentResponse, tags=["Tools"])
async def enrich_address(
    request: DataEnrichmentRequest,
    service=Depends(get_data_enrichment_service),
):
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Data enrichment disabled",
        )
    address = request.address.strip()
    if not address:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="address is required",
        )
    data = service.enrich(address)
    return DataEnrichmentResponse(address=address, data=data)


@router.post("/tools/crm-sync-contact", response_model=CRMContactResponse, tags=["Tools"])
async def crm_sync_contact(
    request: CRMContactRequest,
    connector=Depends(get_crm_connector),
):
    if connector is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="CRM connector not configured",
        )
    payload = {"name": request.name, "phone": request.phone, "email": request.email}
    cid = connector.sync_contact(payload)
    if not cid:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="CRM sync failed",
        )
    return CRMContactResponse(id=cid)


@router.post("/tools/commute-time", response_model=CommuteTimeResponse, tags=["Tools"])
async def commute_time_analysis(
    request: CommuteTimeRequest,
    store: Annotated[Optional[ChromaPropertyStore], Depends(get_vector_store)],
):
    """
    Calculate commute time from a property to a destination.

    Uses Google Routes API to calculate accurate commute times including
    real-time traffic conditions and transit schedules.
    """
    if not store:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Vector store unavailable",
        )

    property_id = request.property_id.strip()
    if not property_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="property_id is required",
        )

    # Get property coordinates
    docs = store.get_properties_by_ids([property_id])
    if not docs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found",
        )

    md = docs[0].metadata or {}
    origin_lat = md.get("lat")
    origin_lon = md.get("lon")

    if origin_lat is None or origin_lon is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Property coordinates not available",
        )

    # Parse departure time if provided
    from datetime import datetime

    parsed_departure_time = None
    if request.departure_time:
        try:
            parsed_departure_time = datetime.fromisoformat(request.departure_time)
        except ValueError as err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid departure_time format. Use ISO format (e.g., '2024-01-15T08:30:00').",
            ) from err

    # Calculate commute time
    from utils.commute_client import CommuteTimeClient

    client = CommuteTimeClient()
    result = await client.get_commute_time(
        property_id=property_id,
        origin_lat=float(origin_lat),
        origin_lon=float(origin_lon),
        destination_lat=request.destination_lat,
        destination_lon=request.destination_lon,
        mode=request.mode,
        destination_name=request.destination_name,
        departure_time=parsed_departure_time,
    )

    # Convert datetime fields to ISO strings for JSON response
    arrival_str = result.arrival_time.isoformat() if result.arrival_time else None
    departure_str = result.departure_time.isoformat() if result.departure_time else None

    return CommuteTimeResponse(
        result=CommuteTimeResult(
            property_id=result.property_id,
            origin_lat=result.origin_lat,
            origin_lon=result.origin_lon,
            destination_lat=result.destination_lat,
            destination_lon=result.destination_lon,
            destination_name=result.destination_name,
            duration_seconds=result.duration_seconds,
            duration_text=result.duration_text,
            distance_meters=result.distance_meters,
            distance_text=result.distance_text,
            mode=result.mode,
            polyline=result.polyline,
            arrival_time=arrival_str,
            departure_time=departure_str,
        )
    )


@router.post("/tools/commute-ranking", response_model=CommuteRankingResponse, tags=["Tools"])
async def commute_ranking(
    request: CommuteRankingRequest,
    store: Annotated[Optional[ChromaPropertyStore], Depends(get_vector_store)],
):
    """
    Rank multiple properties by commute time to a destination.

    Compares commute times from multiple properties to a common destination
    and returns a ranked list from shortest to longest commute.
    """
    if not store:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Vector store unavailable",
        )

    # Parse property IDs
    property_ids = [pid.strip() for pid in request.property_ids.split(",") if pid.strip()]
    if not property_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one property_id is required",
        )

    # Get property coordinates
    docs = store.get_properties_by_ids(property_ids)
    if not docs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No properties found",
        )

    properties_lat_lon = {}
    for doc in docs:
        md = doc.metadata or {}
        pid = str(md.get("id", ""))
        lat = md.get("lat")
        lon = md.get("lon")

        if pid and lat is not None and lon is not None:
            properties_lat_lon[pid] = (float(lat), float(lon))

    if not properties_lat_lon:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No properties with valid coordinates found",
        )

    # Parse departure time if provided
    from datetime import datetime

    parsed_departure_time = None
    if request.departure_time:
        try:
            parsed_departure_time = datetime.fromisoformat(request.departure_time)
        except ValueError as err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid departure_time format. Use ISO format (e.g., '2024-01-15T08:30:00').",
            ) from err

    # Calculate commute times for all properties
    from utils.commute_client import CommuteTimeClient

    client = CommuteTimeClient()
    rankings = await client.rank_properties_by_commute(
        property_ids=list(properties_lat_lon.keys()),
        properties_lat_lon=properties_lat_lon,
        destination_lat=request.destination_lat,
        destination_lon=request.destination_lon,
        mode=request.mode,
        destination_name=request.destination_name,
        departure_time=parsed_departure_time,
    )

    if not rankings:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to calculate commute times for any properties",
        )

    # Calculate summary statistics
    fastest_duration = rankings[0].duration_seconds if rankings else None
    slowest_duration = rankings[-1].duration_seconds if rankings else None

    # Convert CommuteTimeResult dataclass to API model (with datetime as strings)
    ranking_results = []
    for r in rankings:
        arrival_str = r.arrival_time.isoformat() if r.arrival_time else None
        departure_str = r.departure_time.isoformat() if r.departure_time else None
        ranking_results.append(
            CommuteTimeResult(
                property_id=r.property_id,
                origin_lat=r.origin_lat,
                origin_lon=r.origin_lon,
                destination_lat=r.destination_lat,
                destination_lon=r.destination_lon,
                destination_name=r.destination_name,
                duration_seconds=r.duration_seconds,
                duration_text=r.duration_text,
                distance_meters=r.distance_meters,
                distance_text=r.distance_text,
                mode=r.mode,
                polyline=r.polyline,
                arrival_time=arrival_str,
                departure_time=departure_str,
            )
        )

    return CommuteRankingResponse(
        destination_name=request.destination_name,
        destination_lat=request.destination_lat,
        destination_lon=request.destination_lon,
        mode=request.mode,
        rankings=ranking_results,
        count=len(ranking_results),
        fastest_duration_seconds=fastest_duration,
        slowest_duration_seconds=slowest_duration,
    )


# ============================================================================
# Task #114: OSRM-based Commute Analysis (free, no API key)
# ============================================================================


class OSRMCommuteRequest(BaseModel):
    """Request model for OSRM commute analysis."""

    origin_lat: float = Field(..., ge=-90, le=90, description="Origin latitude")
    origin_lon: float = Field(..., ge=-180, le=180, description="Origin longitude")
    destination_lat: float = Field(..., ge=-90, le=90, description="Destination latitude")
    destination_lon: float = Field(..., ge=-180, le=180, description="Destination longitude")
    mode: str = Field(
        default="car",
        description="Travel mode: 'car'/'driving', 'bike'/'bicycling', or 'foot'/'walking'",
    )
    destination_name: Optional[str] = Field(None, description="Human-readable destination name")


class OSRMCommuteResponse(BaseModel):
    """Response model for OSRM commute analysis."""

    duration_seconds: int = Field(..., description="Travel time in seconds")
    duration_minutes: int = Field(..., description="Travel time in minutes")
    distance_km: float = Field(..., description="Distance in kilometers")
    mode: str
    destination_name: Optional[str] = None
    data_source: str = Field(..., description="Data source used: 'osrm' or 'haversine' (fallback)")
    geometry: Optional[str] = Field(None, description="Route geometry (GeoJSON coordinates)")


@router.post("/tools/commute", response_model=OSRMCommuteResponse, tags=["Tools"])
async def osrm_commute_analysis(request: OSRMCommuteRequest):
    """
    Calculate commute time using OSRM (Open Source Routing Machine).

    Free alternative to Google Routes API -- no API key required.
    Supports car, bike, and foot travel modes.
    Falls back to Haversine estimation when OSRM is unavailable.
    """
    try:
        from tools.commute_tool import calculate_commute

        result = await calculate_commute(
            origin_lat=request.origin_lat,
            origin_lon=request.origin_lon,
            destination_lat=request.destination_lat,
            destination_lon=request.destination_lon,
            mode=request.mode,
        )

        return OSRMCommuteResponse(
            duration_seconds=result["duration_seconds"],
            duration_minutes=result["duration_seconds"] // 60,
            distance_km=result["distance_km"],
            mode=request.mode,
            destination_name=request.destination_name,
            data_source=result.get("data_source", "osrm"),
            geometry=result.get("geometry"),
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Commute analysis failed: {str(e)}",
        ) from e


# ============================================================================
# Task #54: Listing Generation
# ============================================================================

# Tone options supported by the tools
LISTING_TONES = ["professional", "friendly", "luxury", "engaging"]
# Languages supported by the tools
LISTING_LANGUAGES = ["en", "pl", "es", "de", "fr", "it", "pt", "ru"]
# Headline styles
HEADLINE_STYLES = ["catchy", "professional", "seo"]
# Social media platforms
SOCIAL_PLATFORMS = ["facebook", "instagram", "linkedin", "twitter"]


class ListingGenerationRequest(BaseModel):
    """Request for generating property listing content."""

    property_id: str
    tone: str = "professional"
    language: str = "en"
    generate_description: bool = True
    generate_headlines: bool = True
    headline_count: int = 5
    headline_style: str = "catchy"
    generate_social: bool = True
    social_platform: str = "facebook"


class ListingGenerationResponse(BaseModel):
    """Response with generated listing content."""

    description: Optional[str] = None
    headlines: Optional[List[str]] = None
    social_content: Optional[str] = None
    char_counts: dict[str, int] = {}
    error: Optional[str] = None


@router.post(
    "/tools/generate-listing",
    response_model=ListingGenerationResponse,
    tags=["Tools"],
)
async def generate_listing(
    request: ListingGenerationRequest,
    store: Annotated[Optional[ChromaPropertyStore], Depends(get_vector_store)],
    llm: Annotated[BaseChatModel, Depends(get_llm)],
):
    """
    Generate AI-powered listing content for a property.

    Generates:
    - Property description with customizable tone and language
    - Multiple headline variants
    - Platform-specific social media content

    All generated content respects platform character limits.
    """
    if not store:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Vector store unavailable",
        )

    # Validate inputs
    if request.tone not in LISTING_TONES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tone. Supported: {', '.join(LISTING_TONES)}",
        )
    if request.language not in LISTING_LANGUAGES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(f"Invalid language. Supported: {', '.join(LISTING_LANGUAGES)}"),
        )
    if request.headline_style not in HEADLINE_STYLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(f"Invalid headline style. Supported: {', '.join(HEADLINE_STYLES)}"),
        )
    if request.social_platform not in SOCIAL_PLATFORMS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(f"Invalid social platform. Supported: {', '.join(SOCIAL_PLATFORMS)}"),
        )

    property_id = request.property_id.strip()
    if not property_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="property_id is required",
        )

    # Fetch property from vector store
    docs = store.get_properties_by_ids([property_id])
    if not docs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found",
        )

    # Convert property to text for the tools
    md = docs[0].metadata or {}

    # Build property data string
    property_parts = []
    if md.get("city"):
        loc = f"{md.get('city')}, {md.get('country', '')}"
        property_parts.append(f"Location: {loc}")
    if md.get("property_type"):
        property_parts.append(f"Type: {md.get('property_type')}")
    if md.get("rooms"):
        property_parts.append(f"Rooms: {md.get('rooms')}")
    if md.get("bathrooms"):
        property_parts.append(f"Bathrooms: {md.get('bathrooms')}")
    if md.get("area_sqm"):
        property_parts.append(f"Area: {md.get('area_sqm')} sqm")
    if md.get("price"):
        price_str = f"{md.get('price')} {md.get('currency', 'EUR')}"
        property_parts.append(f"Price: {price_str}")
    if md.get("year_built"):
        property_parts.append(f"Year built: {md.get('year_built')}")

    # Add amenities
    amenities = []
    if md.get("has_parking"):
        amenities.append("parking")
    if md.get("has_garden"):
        amenities.append("garden")
    if md.get("has_balcony"):
        amenities.append("balcony")
    if md.get("has_elevator"):
        amenities.append("elevator")
    if md.get("has_pool"):
        amenities.append("pool")
    if md.get("is_furnished"):
        amenities.append("furnished")
    if amenities:
        property_parts.append(f"Amenities: {', '.join(amenities)}")

    # Add existing description if available
    if md.get("description"):
        property_parts.append(f"Description: {md.get('description')}")

    property_data = "\n".join(property_parts)

    # Initialize tools
    description_tool = PropertyDescriptionGeneratorTool(llm=llm)
    headline_tool = HeadlineGeneratorTool(llm=llm)
    social_tool = SocialMediaContentGeneratorTool(llm=llm)

    # Generate content
    description = None
    headlines = None
    social_content = None
    char_counts: dict[str, int] = {}
    error = None

    try:
        if request.generate_description:
            description = description_tool._run(
                property_data=property_data,
                tone=request.tone,
                language=request.language,
                max_words=150,
            )
            if not description.startswith("Error:"):
                char_counts["description"] = len(description)
            else:
                error = description
                description = None

        if request.generate_headlines and not error:
            headline_result = headline_tool._run(
                property_data=property_data,
                count=request.headline_count,
                style=request.headline_style,
                language=request.language,
            )
            if not headline_result.startswith("Error:"):
                # Parse headlines from result
                headlines = [
                    line.split(" [")[0].strip()
                    for line in headline_result.split("\n")
                    if line.strip() and not line.startswith("Error:")
                ]
                hl_len = sum(len(h) for h in headlines) if headlines else 0
                char_counts["headlines"] = hl_len
            else:
                if not error:
                    error = headline_result

        if request.generate_social and not error:
            social_content = social_tool._run(
                property_data=property_data,
                platform=request.social_platform,
                tone=request.tone,
                language=request.language,
                include_emojis=True,
                include_call_to_action=True,
            )
            if not social_content.startswith("Error:"):
                # Remove the header line
                if social_content.startswith("=== "):
                    lines = social_content.split("\n")[1:]
                    social_content = "\n".join(lines).strip()
                if social_content:
                    char_counts["social"] = len(social_content)
            else:
                if not error:
                    error = social_content

    except Exception as e:
        error = f"Generation failed: {str(e)}"

    return ListingGenerationResponse(
        description=description,
        headlines=headlines,
        social_content=social_content,
        char_counts=char_counts,
        error=error,
    )


# ============================================================================
# Task #115: Negotiation Helper
# ============================================================================


@router.post("/tools/negotiate", response_model=NegotiationResponse, tags=["Tools"])
async def negotiate(
    request: NegotiationRequest,
    store: Annotated[Optional[ChromaPropertyStore], Depends(get_vector_store)],
):
    """
    Analyse market data for a property and suggest a negotiation strategy.

    Returns:
    - Fair price band (lower / mid / upper)
    - Recommended opening offer
    - Key negotiation arguments
    - Outreach email template based on selected tone
    - Legal disclaimer
    """
    if not store:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Vector store unavailable",
        )

    identifier = request.property_identifier.strip()
    if not identifier:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="property_identifier is required",
        )

    valid_tones = {"formal", "friendly", "assertive"}
    if request.tone not in valid_tones:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tone. Supported: {', '.join(sorted(valid_tones))}",
        )

    tool = NegotiationTool(vector_store=store)
    target, comparables = tool._fetch_property_and_comps(identifier)

    result = NegotiationTool.analyse(
        target=target,
        comparables=comparables,
        user_budget=request.user_budget,
        tone=request.tone,
    )

    return NegotiationResponse(
        property=NegotiationPropertyInfo(**result["property"]),
        price_band=NegotiationPriceBand(**result["price_band"]),
        opening_offer=result.get("opening_offer"),
        arguments=result.get("arguments", []),
        email_template=result.get("email_template"),
        disclaimer=result["disclaimer"],
    )


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
