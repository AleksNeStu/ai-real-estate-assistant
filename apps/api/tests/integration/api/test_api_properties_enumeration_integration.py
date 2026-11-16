"""The catalogue can be enumerated.

`GET /api/v1/properties` is the endpoint the sitemap and the llms.txt are
built from: it is how anything outside the process learns what this
deployment holds. It had no test in any suite the pipeline runs - the only
tests that touched it lived in `tests/performance`, which CI never runs - so
a regression would have emptied the index of a deployment while every gate
stayed green.
"""

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from api.dependencies import get_vector_store
from api.main import app

client = TestClient(app)


def _document(property_id: str, **metadata):
    document = MagicMock()
    document.id = property_id
    document.page_content = f"Listing {property_id}"
    document.metadata = {
        "id": property_id,
        "title": f"Listing {property_id}",
        "city": "Kraków",
        "country": "Poland",
        "price": 322000,
        "currency": "PLN",
        "rooms": 2,
        "area_sqm": 60,
        "lat": 50.0553,
        "lon": 19.9445,
        **metadata,
    }
    return document


def _store(documents):
    store = MagicMock()
    store.search_by_metadata.return_value = documents
    return store


def test_the_catalogue_answers_with_its_listings():
    store = _store([_document("prop-a"), _document("prop-b")])
    app.dependency_overrides[get_vector_store] = lambda: store

    try:
        response = client.get("/api/v1/properties")
    finally:
        app.dependency_overrides.pop(get_vector_store, None)

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 2
    assert [prop["id"] for prop in body["properties"]] == ["prop-a", "prop-b"]
    # The listing carries the fields a listing page reads.
    first = body["properties"][0]
    assert first["city"] == "Kraków"
    assert first["price"] == 322000
    assert first["latitude"] == 50.0553
    assert first["longitude"] == 19.9445


def test_the_catalogue_pages():
    store = _store([_document(f"prop-{index}") for index in range(5)])
    app.dependency_overrides[get_vector_store] = lambda: store

    try:
        response = client.get("/api/v1/properties?limit=2&offset=0")
    finally:
        app.dependency_overrides.pop(get_vector_store, None)

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 2
    assert body["limit"] == 2
    assert body["offset"] == 0
    assert body["has_more"] is True


def test_the_catalogue_needs_no_api_key():
    """A visitor who clicks a listing is nobody until they sign in."""
    store = _store([_document("prop-a")])
    app.dependency_overrides[get_vector_store] = lambda: store

    try:
        response = client.get("/api/v1/properties")
    finally:
        app.dependency_overrides.pop(get_vector_store, None)

    assert response.status_code == 200


def test_the_catalogue_asks_the_store_for_one_page_more():
    """The store cannot say whether there IS a next page, so it is asked for
    one document more than the window."""
    store = _store([_document(f"prop-{index}") for index in range(3)])
    app.dependency_overrides[get_vector_store] = lambda: store

    try:
        client.get("/api/v1/properties?limit=2")
    finally:
        app.dependency_overrides.pop(get_vector_store, None)

    assert store.search_by_metadata.call_args.kwargs["k"] == 3


def test_the_catalogue_says_so_when_the_store_is_gone():
    app.dependency_overrides[get_vector_store] = lambda: None

    try:
        response = client.get("/api/v1/properties")
    finally:
        app.dependency_overrides.pop(get_vector_store, None)

    assert response.status_code == 503
