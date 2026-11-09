"""What the catalogue holds.

The landing page says how many properties, in how many cities, with how many
agents. Those numbers have to come from the catalogue itself: a page that
hardcodes them starts lying the moment the seed changes.

The catalogue is the vector store - that is where the properties the search
answers with actually live. The seeded demo writes them there, and so does the
ingestion pipeline. The JSON cache of the ingestion pipeline is read as a
fallback, for a deployment that has a catalogue file but no vector store yet.
"""

from collections import Counter
from typing import Any, Optional

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_vector_store
from db.database import get_db
from db.models import AgentProfile
from db.schemas import CatalogueStatsResponse, CityCount
from utils.property_cache import load_collection

router = APIRouter(prefix="/catalogue", tags=["Catalogue"])

# How many documents the city and currency counts are read from. A catalogue
# bigger than this reports the true total and the counts of the sample.
_COUNT_SAMPLE_LIMIT = 20000


def _count_from_vector_store(store: Any) -> tuple[int, Counter[str], set[str]]:
    """The total, the cities and the currencies of the vector store."""
    if store is None or not hasattr(store, "vector_store"):
        return 0, Counter(), set()

    vector_store = getattr(store, "vector_store", None)
    if vector_store is None:
        return 0, Counter(), set()

    collection = getattr(vector_store, "_collection", None)
    if collection is None:
        return 0, Counter(), set()

    total = int(collection.count())
    raw = collection.get(include=["metadatas"], limit=_COUNT_SAMPLE_LIMIT) or {}
    metadatas = raw.get("metadatas") or []

    cities: Counter[str] = Counter()
    currencies: set[str] = set()
    for metadata in metadatas:
        if not metadata:
            continue
        city = metadata.get("city")
        if city:
            cities[str(city)] += 1
        currency = metadata.get("currency")
        if currency:
            currencies.add(str(currency))

    return total, cities, currencies


def _count_from_cache() -> tuple[int, Counter[str], set[str]]:
    """The total, the cities and the currencies of the catalogue file."""
    collection = load_collection()
    properties = list(collection.properties) if collection else []
    cities: Counter[str] = Counter(prop.city for prop in properties if prop.city)
    currencies = {str(prop.currency) for prop in properties if prop.currency}
    return len(properties), cities, currencies


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
async def catalogue_stats(
    session: AsyncSession = Depends(get_db),
    store: Optional[Any] = Depends(get_vector_store),
) -> CatalogueStatsResponse:
    """The numbers the landing shows."""
    total, cities, currencies = _count_from_vector_store(store)
    if total == 0:
        total, cities, currencies = _count_from_cache()

    agents: Optional[int] = await session.scalar(select(func.count()).select_from(AgentProfile))

    return CatalogueStatsResponse(
        total=total,
        agents=int(agents or 0),
        cities=[
            CityCount(name=name, count=count)
            for name, count in sorted(cities.items(), key=lambda item: (-item[1], item[0]))
        ],
        currencies=sorted(currencies),
    )
