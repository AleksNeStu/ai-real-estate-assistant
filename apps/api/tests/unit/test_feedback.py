"""Tests for feedback and relevance rating endpoints (Task #118)."""

import os

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("API_ACCESS_KEY", "dev-secret-key")
os.environ.setdefault("ENABLE_JWT_AUTH", "true")

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from db.database import Base, create_engine, get_db
from db.models import SearchFeedback  # noqa: F401 — register model with Base

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
API_KEY = "dev-secret-key"
HEADERS = {"X-API-Key": API_KEY}


@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_engine(TEST_DATABASE_URL, echo=False, connect_args={"check_same_thread": False})
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    from fastapi import Depends, FastAPI

    from api.auth import get_api_key
    from api.routers.feedback import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1", dependencies=[Depends(get_api_key)])

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_submit_rating_valid(client: AsyncClient):
    """Test submitting a valid rating."""
    resp = await client.post(
        "/api/v1/feedback/rating",
        headers=HEADERS,
        json={"query": "apartments in Krakow", "property_id": "prop-123", "rating": 5},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["query"] == "apartments in Krakow"
    assert data["property_id"] == "prop-123"
    assert data["rating"] == 5
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_submit_rating_thumbs_down(client: AsyncClient):
    """Test submitting a thumbs-down (rating=1)."""
    resp = await client.post(
        "/api/v1/feedback/rating",
        headers=HEADERS,
        json={"query": "cheap flat", "property_id": "prop-456", "rating": 1},
    )
    assert resp.status_code == 201
    assert resp.json()["rating"] == 1


@pytest.mark.asyncio
async def test_submit_rating_invalid_too_high(client: AsyncClient):
    """Test rating above 5 is rejected."""
    resp = await client.post(
        "/api/v1/feedback/rating",
        headers=HEADERS,
        json={"query": "test", "property_id": "p1", "rating": 6},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_submit_rating_invalid_zero(client: AsyncClient):
    """Test rating 0 is rejected."""
    resp = await client.post(
        "/api/v1/feedback/rating",
        headers=HEADERS,
        json={"query": "test", "property_id": "p1", "rating": 0},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_submit_rating_missing_fields(client: AsyncClient):
    """Test missing required fields returns 422."""
    resp = await client.post(
        "/api/v1/feedback/rating",
        headers=HEADERS,
        json={"query": "test"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_submit_rating_no_auth(client: AsyncClient):
    """Test that no API key returns 401/403."""
    resp = await client.post(
        "/api/v1/feedback/rating",
        json={"query": "test", "property_id": "p1", "rating": 3},
    )
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_get_relevance_metrics_empty(client: AsyncClient):
    """Test metrics endpoint with no data."""
    resp = await client.get("/api/v1/feedback/metrics/relevance", headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_ratings"] == 0
    assert data["avg_rating"] == 0.0
    assert data["positive_pct"] == 0.0


@pytest.mark.asyncio
async def test_get_relevance_metrics_with_data(client: AsyncClient):
    """Test metrics aggregation with multiple ratings."""
    # Submit 3 positive, 1 negative
    for r in [5, 4, 5, 2]:
        await client.post(
            "/api/v1/feedback/rating",
            headers=HEADERS,
            json={"query": "test query", "property_id": f"p-{r}", "rating": r},
        )

    resp = await client.get("/api/v1/feedback/metrics/relevance", headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_ratings"] == 4
    assert data["avg_rating"] == 4.0
    assert data["positive_pct"] == 75.0  # 3 out of 4 are 4-5
    assert data["ratings_by_score"]["5"] == 2
    assert data["ratings_by_score"]["4"] == 1
    assert data["ratings_by_score"]["2"] == 1


@pytest.mark.asyncio
async def test_get_relevance_metrics_with_since_filter(client: AsyncClient):
    """Test metrics with date filter."""
    # Submit a rating
    await client.post(
        "/api/v1/feedback/rating",
        headers=HEADERS,
        json={"query": "test", "property_id": "p1", "rating": 5},
    )

    # Filter from far future — should return 0
    resp = await client.get(
        "/api/v1/feedback/metrics/relevance",
        headers=HEADERS,
        params={"since": "2099-01-01T00:00:00Z"},
    )
    assert resp.status_code == 200
    assert resp.json()["total_ratings"] == 0

    # Filter from far past — should return 1
    resp = await client.get(
        "/api/v1/feedback/metrics/relevance",
        headers=HEADERS,
        params={"since": "2020-01-01T00:00:00Z"},
    )
    assert resp.status_code == 200
    assert resp.json()["total_ratings"] == 1


@pytest.mark.asyncio
async def test_get_relevance_metrics_invalid_since(client: AsyncClient):
    """Test metrics with invalid date format returns 400."""
    resp = await client.get(
        "/api/v1/feedback/metrics/relevance",
        headers=HEADERS,
        params={"since": "not-a-date"},
    )
    assert resp.status_code == 400
