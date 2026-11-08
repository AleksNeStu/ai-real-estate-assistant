"""What the catalogue holds.

The landing page says how many properties, in how many cities, with how many
agents. Those numbers have to come from the catalogue itself: a page that
hardcodes them starts lying the moment the seed changes.
"""

from collections import Counter
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from db.models import AgentProfile
from db.schemas import CatalogueStatsResponse, CityCount
from utils.property_cache import load_collection

router = APIRouter(prefix="/catalogue", tags=["Catalogue"])


@router.get(
    "/stats",
    response_model=CatalogueStatsResponse,
    summary="What the catalogue holds",
    description=(
        "The live numbers of the catalogue: the properties, the cities they "
        "are in, the agents and the currencies. An empty catalogue answers "
        "with zeros rather than an error."
    ),
)
async def catalogue_stats(session: AsyncSession = Depends(get_db)) -> CatalogueStatsResponse:
    """The numbers the landing shows."""
    collection = load_collection()
    properties = list(collection.properties) if collection else []

    cities = Counter(prop.city for prop in properties if prop.city)
    currencies = sorted({str(prop.currency) for prop in properties if prop.currency})

    agents: Optional[int] = await session.scalar(select(func.count()).select_from(AgentProfile))

    return CatalogueStatsResponse(
        total=len(properties),
        agents=int(agents or 0),
        cities=[
            CityCount(name=name, count=count)
            for name, count in sorted(cities.items(), key=lambda item: (-item[1], item[0]))
        ],
        currencies=currencies,
    )
