"""The report has to find the comparables the wizard showed.

The wizard asked for a comparable of 40 points and above, the report drew from
50 and answered "Found only 0 comparables, need at least 3" - a demo in which
the operator sees a comparable and the report then refuses it. One bar serves
both now, and this test holds it.
"""

from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from analytics.comparable_selector import ComparableSelector
from api.dependencies import get_vector_store  # noqa: F401  (documents where the store comes from)
from api.deps.auth import get_current_active_user
from api.routers import cma
from data.schemas import Property, PropertyCollection
from db.database import get_db
from db.schemas import UserResponse

SUBJECT_ID = "prop-subject"

# The subject: an apartment of 60 square metres in the Old Town of Kraków.
SUBJECT_METADATA = {
    "id": SUBJECT_ID,
    "title": "Subject",
    "property_type": "apartment",
    "listing_type": "sale",
    "price": 500000,
    "currency": "PLN",
    "area_sqm": 60,
    "rooms": 3,
    "bathrooms": 1,
    "city": "Kraków",
    "district": "Old Town",
    "latitude": 50.0625,
    "longitude": 19.9390,
    "year_built": 2015,
    "floor": 3,
    "total_floors": 10,
    "energy_rating": "B",
    "has_parking": False,
    "has_garden": False,
    "has_elevator": False,
    "has_balcony": False,
    "is_furnished": False,
    "has_pool": False,
    "has_garage": False,
    "pets_allowed": False,
}


def _document(property_id: str, **overrides):
    metadata = dict(SUBJECT_METADATA)
    metadata.update(overrides)
    metadata["id"] = property_id
    return SimpleNamespace(id=property_id, page_content=f"Listing {property_id}", metadata=metadata)


def _comparable(property_id: str) -> SimpleNamespace:
    """A comparable that scores between 40 and 50.

    It stands six kilometres away (0 points), is of another type (0), has a
    fifth more space (10), the same number of rooms (15), was listed today
    (15) and shares only half of its amenities (5.6). That is 45.6 points: the
    wizard showed it, the stricter bar of the report threw it away.
    """
    return _document(
        property_id,
        property_type="house",
        price=480000,
        area_sqm=72,
        latitude=50.1200,
        longitude=19.9390,
        has_parking=True,
        has_pool=True,
        has_garage=True,
        has_elevator=True,
    )


@pytest.fixture
def mock_vector_store():
    documents = [_document(SUBJECT_ID)] + [_comparable(f"prop-{index}") for index in range(1, 4)]
    store = SimpleNamespace(
        get_properties_by_ids=lambda ids: [d for d in documents if d.id in ids],
        search_by_metadata=lambda **kwargs: documents,
    )
    return store


@pytest.fixture
def test_app(db_session, mock_vector_store, monkeypatch):
    app = FastAPI()
    app.include_router(cma.router, prefix="/api/v1")

    # The CMA router asks for the vector store itself instead of taking it as a
    # dependency, so the override of the app cannot reach it - the function has
    # to be replaced where the router looks it up.
    monkeypatch.setattr(cma, "get_vector_store", lambda: mock_vector_store)

    async def override_get_db():
        yield db_session

    async def override_get_current_user():
        return UserResponse(
            id="test-user-123",
            email="test@example.com",
            roles=["user"],
            created_at="2024-01-01T00:00:00Z",
        )

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_active_user] = override_get_current_user
    return app


@pytest.fixture
async def client(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def test_the_comparables_of_the_fixture_sit_between_the_two_bars():
    """The fixture only proves something while it lands between 40 and 50."""
    subject = Property(**SUBJECT_METADATA)
    candidates = [Property(**{**_comparable(f"prop-{index}").metadata}) for index in range(1, 4)]
    collection = PropertyCollection(
        properties=candidates, total_count=len(candidates), source_type="vector_store"
    )  # type: ignore[call-arg]
    scores = ComparableSelector(collection).find_comparables(
        subject=subject,
        max_distance_km=5.0,
        min_score=0.0,
        max_results=10,
    )
    assert scores, "the fixture has to produce a comparable at all"
    for score in scores:
        assert 40.0 <= score.total_score < 50.0, f"{score.property_id} scored {score.total_score}"


def test_the_endpoint_and_the_report_share_one_bar():
    """One number decides what a comparable is - the wizard, the endpoint, the report."""
    assert cma.CMA_SUGGESTION_MIN_SCORE == 40.0

    schema = FastAPI()
    schema.include_router(cma.router, prefix="/api/v1")
    parameters = schema.openapi()["paths"]["/api/v1/cma/comparables/{property_id}"]["post"][
        "parameters"
    ]
    min_score = next(p for p in parameters if p["name"] == "min_score")
    assert min_score["schema"]["default"] == cma.CMA_SUGGESTION_MIN_SCORE


@pytest.mark.asyncio
async def test_the_report_finds_a_comparable_the_wizard_would_show(client):
    """The report answers with a report, not with "Found only 0 comparables"."""
    response = await client.post(
        "/api/v1/cma/generate",
        json={"subject_property_id": SUBJECT_ID},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body["comparables"]) == 3
    assert body["valuation"]["comparables_count"] == 3


@pytest.mark.asyncio
async def test_the_comparables_endpoint_shows_them_by_default(client):
    """The endpoint without a score of its own shows what the wizard shows."""
    response = await client.post(f"/api/v1/cma/comparables/{SUBJECT_ID}")
    assert response.status_code == 200, response.text
    assert len(response.json()) == 3
