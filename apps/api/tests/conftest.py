"""
Pytest configuration and shared fixtures.
"""

# CRITICAL: Set test environment BEFORE any imports that might load settings
import os

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("API_ACCESS_KEY", "dev-secret-key")
os.environ.setdefault("ENABLE_JWT_AUTH", "true")

import importlib
import importlib.util
import sys
import types
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from langchain_core.documents import Document
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from agents.query_analyzer import QueryAnalyzer
from core.jwt import create_access_token
from data.schemas import Property, PropertyCollection, PropertyType
from db.database import Base
from db.models import (
    DataSourceDB,  # noqa: F401 - Import to register model with Base (Task #79)
    DataSourceSyncHistory,  # noqa: F401 - Import to register model with Base (Task #79)
    MarketAnomaly,  # noqa: F401 - Import to register model with Base
)
from vector_store.reranker import PropertyReranker


def _install_stub_module(module_name: str, attrs: dict[str, object] | None = None) -> None:
    if module_name in sys.modules:
        return
    module = types.ModuleType(module_name)
    if module_name == "odf":
        module.__path__ = []
    if attrs:
        for key, value in attrs.items():
            setattr(module, key, value)
    sys.modules[module_name] = module
    if "." in module_name:
        parent_name, child_name = module_name.rsplit(".", 1)
        parent = sys.modules.get(parent_name)
        if parent is None:
            parent = types.ModuleType(parent_name)
            parent.__path__ = []
            sys.modules[parent_name] = parent
        setattr(parent, child_name, module)


def _ensure_optional_excel_modules() -> None:
    if importlib.util.find_spec("xlrd") is None:
        book_type = type("Book", (), {})
        _install_stub_module(
            "xlrd",
            {
                "open_workbook": lambda *_args, **_kwargs: book_type(),
                "__version__": "2.0.1",
                "Book": book_type,
            },
        )
    if importlib.util.find_spec("odf") is None:
        _install_stub_module("odf")
    try:
        odf_opendocument = importlib.import_module("odf.opendocument")
    except Exception:
        _install_stub_module("odf.opendocument", {"load": lambda *_args, **_kwargs: None})
    else:
        parent = sys.modules.get("odf")
        child = sys.modules.get("odf.opendocument", odf_opendocument)
        if parent is not None and child is not None and not hasattr(parent, "opendocument"):
            setattr(parent, "opendocument", child)  # noqa: B010


def pytest_configure() -> None:
    """Pytest configuration hook."""
    # Env vars are set at module level above, before any imports
    _ensure_optional_excel_modules()


@pytest.fixture
def query_analyzer():
    """Fixture for query analyzer."""
    return QueryAnalyzer()


@pytest.fixture
def sample_properties():
    """Fixture for sample property data."""
    properties = [
        Property(
            id="prop1",
            city="Krakow",
            rooms=2,
            bathrooms=1,
            price=950,
            area_sqm=55,
            has_parking=True,
            has_garden=False,
            property_type=PropertyType.APARTMENT,
            source_url="http://example.com/1",
        ),
        Property(
            id="prop2",
            city="Krakow",
            rooms=2,
            bathrooms=1,
            price=890,
            area_sqm=48,
            has_parking=False,
            has_garden=True,
            property_type=PropertyType.APARTMENT,
            source_url="http://example.com/2",
        ),
        Property(
            id="prop3",
            city="Warsaw",
            rooms=3,
            bathrooms=2,
            price=1350,
            area_sqm=75,
            has_parking=True,
            has_garden=False,
            property_type=PropertyType.APARTMENT,
            source_url="http://example.com/3",
        ),
        Property(
            id="prop4",
            city="Krakow",
            rooms=1,
            bathrooms=1,
            price=650,
            area_sqm=35,
            has_parking=False,
            has_garden=False,
            property_type=PropertyType.STUDIO,
            source_url="http://example.com/4",
        ),
        Property(
            id="prop5",
            city="Warsaw",
            rooms=2,
            bathrooms=1,
            price=1100,
            area_sqm=60,
            has_parking=True,
            has_garden=True,
            property_type=PropertyType.APARTMENT,
            source_url="http://example.com/5",
        ),
    ]
    return PropertyCollection(properties=properties, total_count=5)


@pytest.fixture
def sample_documents(sample_properties):
    """Fixture for sample documents from properties."""
    documents = []
    for prop in sample_properties.properties:
        doc = Document(
            page_content=prop.to_search_text(),
            metadata=prop.to_dict(),
        )
        documents.append(doc)
    return documents


@pytest.fixture
def reranker():
    """Fixture for property reranker."""
    return PropertyReranker()


# === Async Database Fixtures ===

# Use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="function", autouse=True)
def clear_lru_caches() -> None:
    """Clear all lru_cache instances before each test.

    Prevents test isolation issues when tests run in parallel.
    Particularly important for get_vector_store() and get_knowledge_store().
    """
    from api.dependencies import (
        clear_knowledge_store_cache,
        clear_llm_cache,
        clear_vector_store_cache,
    )

    clear_vector_store_cache()
    clear_knowledge_store_cache()
    clear_llm_cache()
    yield
    # Clear again after test
    clear_vector_store_cache()
    clear_knowledge_store_cache()
    clear_llm_cache()


@pytest.fixture(scope="function", autouse=True)
def reset_free_tier_rate_limiter() -> None:
    """Start every test with an empty free-tier counter.

    The limiter counts anonymous chat requests per address, and in a test
    process every request carries the same address. Without a reset the
    counter fills up during the suite and the limit trips on a test that has
    nothing to do with rate limiting - the chat router's own suite fails at
    the twenty-first request.
    """
    from utils.free_tier import get_free_tier_rate_limiter

    limiter = get_free_tier_rate_limiter()
    limiter.reset()
    yield
    limiter.reset()


@pytest.fixture(scope="function", autouse=True)
def reset_api_rate_limiter() -> None:
    """Start every test with an empty API counter and the deployment's rate.

    The middleware counts every request by address, and in a test process
    every request carries the same address. The counter fills up during the
    suite, and the tests that exercise the limit lower the rate for their
    own run - a rate the next test would otherwise inherit and be held to.
    """
    import sys

    module = sys.modules.get("api.main")
    if module is None:
        # The application is not imported yet, so it has no limiter to reset.
        yield
        return

    limiter = getattr(module.app.state, "rate_limiter", None)
    if limiter is None:
        yield
        return

    default_rpm = limiter.default_rpm
    limiter.reset()
    yield
    limiter.reset()
    limiter.default_rpm = default_rpm


@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh database session for each test."""
    # Create test engine
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False},
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session
    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with session_factory() as session:
        yield session

    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture(scope="function")
async def async_client(
    db_session: AsyncSession,
) -> AsyncGenerator[AsyncClient, None]:
    """Create an async HTTP client for testing API endpoints."""
    from fastapi import FastAPI

    from api.deps.auth import get_current_active_user
    from api.routers import market
    from db.database import get_db
    from db.schemas import UserResponse

    # Create a fresh test app with the market router
    test_app = FastAPI()
    test_app.include_router(market.router, prefix="/api/v1")

    # Override the get_db dependency
    async def override_get_db():
        yield db_session

    # Override auth to return a mock user
    async def override_get_current_user():
        return UserResponse(
            id="test-user-123",
            email="test@example.com",
            roles=["user"],
            created_at="2024-01-01T00:00:00Z",
        )

    test_app.dependency_overrides[get_db] = override_get_db
    test_app.dependency_overrides[get_current_active_user] = override_get_current_user

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    # Cleanup
    test_app.dependency_overrides.clear()


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Create authentication headers for testing."""
    token = create_access_token(subject="test-user-123", roles=["user"])
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
async def unauth_client() -> AsyncGenerator[AsyncClient, None]:
    """Create an unauthenticated async HTTP client for testing auth
    requirements."""
    from fastapi import FastAPI

    from api.routers import market

    # Create a fresh test app with the market router (no auth override)
    test_app = FastAPI()
    test_app.include_router(market.router, prefix="/api/v1")

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


# =============================================================================
# Fixtures for User Activity Analytics (Task #82)
# =============================================================================


@pytest.fixture
def user_activity_service(db_session):
    """Create a UserActivityService instance for testing.

    Task #82: User Activity Analytics
    """
    from services.user_activity_service import UserActivityService

    return UserActivityService(db_session, retention_days=30)
