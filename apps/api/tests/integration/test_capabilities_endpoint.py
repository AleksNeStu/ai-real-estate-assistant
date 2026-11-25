"""
The capabilities endpoint against the running application.

The endpoint describes the running deployment, so the test gives it one: a
database that holds a sale of the register, and a database that holds none.
The answer has to follow the database - a constant in the test would prove
nothing about the deployment the endpoint answers for.
"""

from datetime import date

import pytest
from httpx import ASGITransport, AsyncClient

from api.main import app
from api.routers import capabilities
from data.places import PLACES
from data.rcn.rcn_models import normalize_text
from db.database import get_db
from db.models import PropertyTransaction

# The formats the import chain reads with a spreadsheet reader, and the one
# it reads with the CSV loader.
SPREADSHEET_FORMATS = {".xlsx", ".xls", ".ods"}


@pytest.fixture(autouse=True)
def _no_cached_register_answer():
    """The register answer is kept for a minute; every test reads it fresh."""
    capabilities._register_cache = None
    yield
    capabilities._register_cache = None


@pytest.fixture
async def client(db_session):
    """The real application, reading the database the test owns."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


def _sale(city: str, external_id: str) -> PropertyTransaction:
    """A sale the register holds in the given city."""
    return PropertyTransaction(
        external_id=external_id,
        transaction_id=f"deed-{external_id}",
        city=city,
        city_norm=normalize_text(city),
        street="Floriańska",
        street_norm=normalize_text("Floriańska"),
        area_sqm=50.0,
        price_brutto=500000.0,
        transaction_date=date(2024, 5, 1),
    )


async def test_the_demo_flags_are_published_split(client):
    response = await client.get("/api/v1/capabilities")

    assert response.status_code == 200
    body = response.json()
    assert "demo_llm_mode" in body["llm"]
    assert "demo_mode" not in body["llm"]
    assert "demo_data_mode" in body["data"]


async def test_the_ingestion_formats_are_published(client):
    response = await client.get("/api/v1/capabilities")

    assert response.status_code == 200
    ingest = response.json()["ingest"]
    assert set(ingest["formats"]) <= SPREADSHEET_FORMATS | {".csv"}
    assert ".csv" in ingest["formats"]
    assert ingest["excel"] is bool(set(ingest["formats"]) & SPREADSHEET_FORMATS)


async def test_a_deployment_that_stored_no_sale_holds_no_register(client):
    # The register is read from the stored sales. Nothing is stored, so the
    # deployment holds no register and does not offer it.
    response = await client.get("/api/v1/capabilities")

    assert response.status_code == 200
    assert response.json()["ingest"]["register"] is False


async def test_a_deployment_that_stored_a_sale_holds_the_register(client, db_session):
    # The answer follows the database: a sale of a city the site knows makes
    # the register readable, and the deployment says so.
    place = next(place for place in PLACES if place.register_city)
    db_session.add(_sale(place.register_city, f"rcn-{place.name}"))
    await db_session.commit()

    response = await client.get("/api/v1/capabilities")

    assert response.status_code == 200
    assert response.json()["ingest"]["register"] is True


async def test_a_sale_of_a_city_the_site_does_not_know_is_not_the_register(client, db_session):
    # A register source names a city, and a source of a city the site does
    # not know cannot be read at all - the data-source router refuses it
    # with "unknown city". So the register is readable for the cities the
    # site knows, and a sale of another city does not make it readable.
    db_session.add(_sale("SZCZECIN", "rcn-szczecin"))
    await db_session.commit()

    response = await client.get("/api/v1/capabilities")

    assert response.status_code == 200
    assert response.json()["ingest"]["register"] is False


async def test_a_deployment_that_could_not_be_asked_says_so(client, monkeypatch):
    # The database could not be asked about the register. The answer is the
    # unknown one - null - and not "the deployment holds none": a deployment
    # that could not be asked is not a deployment that holds nothing. The
    # request still ends in an answer and not in a server error.
    async def failing(session, city_norms, until=None):
        raise RuntimeError("the database is away")

    monkeypatch.setattr("db.property_transaction_repo.has_sales_of_cities", failing)

    response = await client.get("/api/v1/capabilities")

    assert response.status_code == 200
    assert response.json()["ingest"]["register"] is None
