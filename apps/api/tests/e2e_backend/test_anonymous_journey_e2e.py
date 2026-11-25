"""
The anonymous journey of the product, as a test.

The public demo answers a visitor with no account. That was a belief, and a
belief does not survive a release: this module is the proof.

The request a visitor's browser makes carries the key of the deployment - the
Next.js proxy injects it server-side, and it identifies the deployment, not
the visitor - and no session at all: no Authorization header, no
``access_token`` cookie. Every request below is made that way.

Two claims are held here:

* **the public journey answers** - the capabilities, the search, the chat,
  the free chat, the listings, the places, the valuation and the official
  register are reachable without an account, and each one answers with the
  status it is supposed to answer with;
* **the account of the visitor stays his** - the routes that hold what
  belongs to an account answer 401 without a token, even though the request
  carries the key of the deployment.

The suite runs in two modes (see ``conftest.py``): in-process, with the model
and the vector store replaced by mocks, and against a running backend, where
the deployment answers as it is deployed. Both modes are held to the same
claim: the public journey is not turned away for want of an account.
"""

import os

import pytest
import pytest_asyncio
from langchain_core.retrievers import BaseRetriever

# The public journey: the endpoints a visitor with no account reaches, the
# body each one needs, and the statuses that are an answer.
#
# The free chat is on the journey - it is the chat of a visitor who has no
# key either.
PUBLIC_JOURNEY = [
    # What the deployment can do.
    ("GET", "/api/v1/capabilities", None, (200,)),
    # The catalogue the demo answers with.
    ("GET", "/api/v1/properties", None, (200,)),
    ("GET", "/api/v1/catalogue/stats", None, (200,)),
    # The directory of the agents.
    ("GET", "/api/v1/agents", None, (200,)),
    # The cities the register covers. 404 is the answer of a deployment whose
    # register holds nothing yet - it is still an answer, and it is not a
    # request for an account.
    ("GET", "/api/v1/places", None, (200, 404)),
    # The search, the chat and the free chat.
    ("POST", "/api/v1/search", {"query": "apartments in Krakow"}, (200,)),
    # 503 is the answer of a provider that cannot answer at the moment. The
    # request was still not turned away for want of an account.
    ("POST", "/api/v1/chat", {"message": "Which flats are in Krakow?"}, (200, 503)),
    ("POST", "/api/v1/chat/free", {"message": "Which flats are in Krakow?"}, (200, 503)),
    # The official register answers the valuation of a place. 404 is its
    # answer when it holds no registered sale to compare the place with.
    ("POST", "/api/v1/tools/valuation", {"city": "Krakow"}, (200, 404)),
]

# The endpoints that ask the model for an answer.
CHAT_PATHS = ("/api/v1/chat", "/api/v1/chat/free")

# The routes that hold what belongs to an account.
ACCOUNT_ROUTES = [
    "/api/v1/favorites",
    "/api/v1/collections",
    "/api/v1/saved-searches",
    "/api/v1/documents",
    "/api/v1/leads",
    "/api/v1/me/buyer-memory",
    "/api/v1/profile",
    "/api/v1/user-activity/summary",
    "/api/v1/agent-analytics/me",
]


def _assert_no_session(headers: dict[str, str]) -> None:
    """The request carries the key of the deployment and no session of a visitor."""
    names = {name.lower() for name in headers}
    assert "authorization" not in names
    assert "cookie" not in names


def _is_live() -> bool:
    """Whether the suite talks to a running backend rather than the app in-process."""
    return bool(os.environ.get("E2E_BASE_URL", "").strip())


class _EmptyRetriever(BaseRetriever):
    """
    A retriever that finds nothing, and is one.

    The chain that answers a chat is built with a retriever, and LangChain
    refuses a chain whose retriever is not a retriever - the mock of the
    suite is not one, so the chat fails before it is asked anything. This one
    is a real retriever with nothing in it, so the chain is built and the
    answer comes from the model.
    """

    def _get_relevant_documents(self, query, *, run_manager=None):
        return []


@pytest_asyncio.fixture(autouse=True)
async def local_deployment(e2e_client, monkeypatch):
    """
    In-process, the suite answers the way the deployment answers.

    The suite replaces the model with a mock that is not a chat model, and the
    vector store with a mock whose retriever is not a retriever - so the chat
    fails with a 500 before the visitor is asked anything, and a test that
    accepts a 500 proves nothing. Here the model is the local demo model (a
    real chat model, with no key and no network) and the retriever is a real
    one with nothing in it, so the chat answers 200 the way the deployment
    answers it.

    The free chat is a second boundary: it resolves its own provider from the
    cascade of the free tier, and that resolution is a call, not a dependency
    - so the demo model is put in its place as well. Without that, the free
    chat answers 503 on a machine that holds no provider key, and the suite
    would be asserting the keyring of the machine it runs on.

    Against a running backend nothing is replaced: the deployment answers with
    the model it is configured with.
    """
    if _is_live():
        yield
        return

    from unittest.mock import MagicMock

    from api.dependencies import get_llm, get_optional_llm_with_details, get_vector_store
    from api.main import app
    from api.routers import chat as chat_router
    from core.demo import get_demo_llm

    model = get_demo_llm()
    store = MagicMock()
    store.similarity_search_with_score.return_value = []
    store.get_stats.return_value = {"documents": 0}
    store.get_retriever.return_value = _EmptyRetriever()

    previous_overrides = {
        dependency: app.dependency_overrides[dependency]
        for dependency in (get_vector_store, get_llm, get_optional_llm_with_details)
        if dependency in app.dependency_overrides
    }

    app.dependency_overrides[get_vector_store] = lambda: store
    app.dependency_overrides[get_llm] = lambda: model
    app.dependency_overrides[get_optional_llm_with_details] = lambda: (
        model,
        "demo-mock",
        "demo-mock",
    )
    monkeypatch.setattr(chat_router, "get_llm_for_free_user", lambda: model)
    try:
        yield
    finally:
        # The overrides the suite of the product installed are restored, not
        # dropped: a teardown that pops them outright takes away what
        # conftest put there.
        for dependency in (get_vector_store, get_llm, get_optional_llm_with_details):
            if dependency in previous_overrides:
                app.dependency_overrides[dependency] = previous_overrides[dependency]
            else:
                app.dependency_overrides.pop(dependency, None)


@pytest_asyncio.fixture
async def account_is_gated(e2e_client, api_headers) -> bool:
    """
    Whether the target keeps the account of the visitor behind a token.

    A deployment may answer an anonymous request with the synthetic demo user
    (``DEMO_USER_BYPASS``) - and then the account routes do answer, as the
    demo user. The suite asks the target instead of assuming: one request
    without a token, and the answer says whether the account is required
    there. Where it is not, the assertion is skipped with the reason - not
    silently passed, and not turned into its opposite.

    A target that answers neither 401 nor 200 is broken, and it fails here
    rather than skipping: a broken target is not a target that lets the
    account through.
    """
    resp = await e2e_client.get("/api/v1/favorites", headers=api_headers)
    if resp.status_code == 401:
        return True
    if resp.status_code == 200:
        pytest.skip(
            "the target answers an anonymous request as the demo user (DEMO_USER_BYPASS) - "
            "the account is asserted where the account is required"
        )
    pytest.fail(
        f"the target answered {resp.status_code} for an anonymous request to the favourites - "
        "the contract of a missing session is 401, and a broken target is not a target that "
        "lets the account through"
    )


@pytest.mark.asyncio
class TestAnonymousJourneyE2E:
    """The public journey answers for a visitor with no account."""

    async def test_the_request_carries_no_session(self, e2e_client, api_headers):
        """The key of the deployment is not a session of a visitor."""
        _assert_no_session(api_headers)
        # The shared client must not carry a session either: a cookie or a
        # default header on the client would put a session into every request
        # of the suite, and the claim above would be about the headers of one
        # request only.
        assert not e2e_client.cookies, f"the client carries cookies: {list(e2e_client.cookies)}"

    async def test_every_route_of_the_journey_exists(self, e2e_client):
        """
        A route that does not exist answers 404 - and a test that accepts 404
        proves nothing. So the journey is held against the schema of the
        deployment: every path it names is a path the API really serves.
        """
        resp = await e2e_client.get("/openapi.json")
        assert resp.status_code == 200
        paths = set(resp.json().get("paths", {}))
        missing = [path for _method, path, _body, _allowed in PUBLIC_JOURNEY if path not in paths]
        missing += [path for path in ACCOUNT_ROUTES if path not in paths]
        assert missing == [], f"the journey names routes the API does not serve: {missing}"

    async def test_the_public_journey_is_not_turned_away(self, e2e_client, api_headers):
        """
        Every endpoint of the public journey answers, and none asks for an
        account.

        Some of them answer with a status that is not a success - a deployment
        whose provider is busy answers 503, a deployment whose register holds
        nothing answers 404. The claim of this test is the one that matters
        for a visitor with no account: none of these answers is 401 or 403.
        A server error is not an answer at all, so it fails here.
        """
        _assert_no_session(api_headers)
        answered = {}
        for method, path, body, allowed in PUBLIC_JOURNEY:
            effective = allowed
            if not _is_live() and path in CHAT_PATHS:
                # In-process the model is the local demo model, and it always
                # answers: 503 there would be a broken chain, not a provider
                # that is busy.
                effective = (200,)
            resp = await e2e_client.request(method, path, json=body, headers=api_headers)
            answered[path] = resp.status_code
            assert resp.status_code in effective, (
                f"{method} {path} answered {resp.status_code}, "
                f"and the journey expects {effective}: {answered}"
            )
            # 401 and 403 are the two answers that mean "come back with an
            # account". Neither may be the answer of the public journey.
            assert resp.status_code not in (401, 403), (
                f"{method} {path} asked a visitor for an account: {answered}"
            )
            # A server error is a broken endpoint, not an answer.
            assert resp.status_code < 500, (
                f"{method} {path} answered {resp.status_code}, "
                f"which is a failure of the endpoint and not an answer: {answered}"
            )
        assert len(answered) == len(PUBLIC_JOURNEY)

    async def test_the_capabilities_answer(self, e2e_client, api_headers):
        resp = await e2e_client.get("/api/v1/capabilities", headers=api_headers)
        assert resp.status_code == 200
        assert "auth" in resp.json()

    async def test_the_search_answers_the_query(self, e2e_client, api_headers):
        resp = await e2e_client.post(
            "/api/v1/search",
            json={"query": "apartments in Krakow"},
            headers=api_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        # The schema of the search is `results` and `count` - so the answer is
        # held to them, not to "something that looks like an answer".
        assert "results" in data and "count" in data, f"the search answered {data}"
        assert isinstance(data["results"], list)

    async def test_the_chat_answers_without_a_session(self, e2e_client, api_headers):
        resp = await e2e_client.post(
            "/api/v1/chat",
            json={"message": "Which flats are in Krakow?"},
            headers=api_headers,
        )
        # In-process the model is the local demo model and it always answers;
        # only a deployment with a provider that is busy may answer 503.
        assert resp.status_code in ((200, 503) if _is_live() else (200,))
        assert resp.status_code not in (401, 403)
        if resp.status_code == 200:
            assert resp.json().get("response")

    async def test_the_free_chat_answers_without_a_session(self, e2e_client, api_headers):
        resp = await e2e_client.post(
            "/api/v1/chat/free",
            json={"message": "Which flats are in Krakow?"},
            headers=api_headers,
        )
        assert resp.status_code in ((200, 503) if _is_live() else (200,))
        assert resp.status_code not in (401, 403)

    async def test_the_listings_answer_without_a_session(self, e2e_client, api_headers):
        resp = await e2e_client.get("/api/v1/properties", headers=api_headers)
        assert resp.status_code == 200

    async def test_the_places_answer_without_a_session(self, e2e_client, api_headers):
        """The places the site knows - the cities the register covers."""
        resp = await e2e_client.get("/api/v1/places", headers=api_headers)
        assert resp.status_code in (200, 404)
        assert resp.status_code not in (401, 403)

    async def test_the_valuation_is_answered_from_the_register(self, e2e_client, api_headers):
        """
        The official register answers the valuation of a place.

        A deployment whose register holds no registered sale to compare the
        place with answers 404 - the register is empty, not broken. Where the
        register answers, its answer is checked: the source is the register
        and it holds samples.
        """
        resp = await e2e_client.post(
            "/api/v1/tools/valuation",
            json={"city": "Krakow"},
            headers=api_headers,
        )
        assert resp.status_code in (200, 404)
        assert resp.status_code not in (401, 403)
        if resp.status_code == 200:
            data = resp.json()
            assert data.get("source") == "rcn"
            assert data.get("sample_size", 0) > 0

    @pytest.mark.usefixtures("account_is_gated")
    async def test_the_account_routes_answer_401_without_a_token(self, e2e_client, api_headers):
        """What belongs to an account stays behind an account."""
        _assert_no_session(api_headers)
        answered = {}
        for path in ACCOUNT_ROUTES:
            resp = await e2e_client.get(path, headers=api_headers)
            answered[path] = resp.status_code
            assert resp.status_code == 401, (
                f"{path} answered {resp.status_code} without a token: {answered}"
            )
        assert len(answered) == len(ACCOUNT_ROUTES)
