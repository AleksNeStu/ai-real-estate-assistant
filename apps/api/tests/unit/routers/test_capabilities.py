"""
Tests for the deployment capabilities endpoint.

Task #34: the frontend must not offer what the deployment cannot serve, so
the backend has to publish the answer.
"""

import sys
from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from api.routers import capabilities
from data.places import PLACES
from data.rcn.rcn_models import normalize_text
from db.database import get_db
from db.models import PropertyTransaction


def _settings(**overrides):
    """A settings stub with the fields the capability builder reads."""
    defaults = {
        "auth_jwt_enabled": False,
        "auth_oauth_google_enabled": False,
        "auth_oauth_apple_enabled": False,
        "google_client_id": None,
        "google_client_secret": None,
        "google_redirect_uri": None,
        "apple_client_id": None,
        "apple_team_id": None,
        "apple_private_key_path": None,
        # The address the callback sends the visitor back to. Without it the
        # browser flow cannot be delivered, so the capability stays off.
        "frontend_url": None,
        "demo_mode": True,
        "demo_llm_mode": False,
        "demo_data_mode": False,
        "demo_user_bypass": False,
        "default_provider": "zai",
        "default_model": "test-model",
        "sentry_dsn": None,
    }
    defaults.update(overrides)
    return MagicMock(**defaults)


@pytest.fixture(autouse=True)
def _no_cached_register_answer():
    """The register answer is kept for a minute; every test reads it fresh."""
    capabilities._register_cache = None
    capabilities._warned_at = None
    yield
    capabilities._register_cache = None
    capabilities._warned_at = None


@pytest.fixture
async def capabilities_client(db_session):
    app = FastAPI()
    app.include_router(capabilities.router, prefix="/api/v1")
    app.state.email_enabled = False

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


class TestBuildCapabilities:
    """The builder is pure — it only reads the settings."""

    def test_oauth_is_off_without_configuration(self):
        with patch.object(capabilities, "get_settings", return_value=_settings()):
            result = capabilities.build_capabilities(email_enabled=False)

        assert result["auth"]["oauth"] == {"google": False, "apple": False}

    def test_a_provider_needs_both_the_flag_and_the_credentials(self):
        # The flag is on but no client id was configured: the endpoint would
        # answer 500, so the capability must stay off.
        with patch.object(
            capabilities,
            "get_settings",
            return_value=_settings(auth_oauth_google_enabled=True),
        ):
            result = capabilities.build_capabilities(email_enabled=False)

        assert result["auth"]["oauth"]["google"] is False

    def test_a_fully_configured_provider_is_reported_as_available(self):
        with patch.object(
            capabilities,
            "get_settings",
            return_value=_settings(
                auth_jwt_enabled=True,
                auth_oauth_google_enabled=True,
                google_client_id="id",
                google_client_secret="secret",  # pragma: allowlist secret
                google_redirect_uri="https://example.test/api/v1/auth/oauth/callback",
                frontend_url="https://app.example.test",
            ),
        ):
            result = capabilities.build_capabilities(email_enabled=False)

        assert result["auth"]["oauth"]["google"] is True
        assert result["auth"]["oauth"]["apple"] is False

    def test_a_provider_without_a_frontend_url_is_not_reported_as_available(self):
        # The callback sends the visitor back to the interface only when the
        # deployment names an address it can redirect to. Without one the
        # click answers with a JSON body - a button that leads to JSON is a
        # dead end, so the browser flow is part of the capability.
        with patch.object(
            capabilities,
            "get_settings",
            return_value=_settings(
                auth_jwt_enabled=True,
                auth_oauth_google_enabled=True,
                google_client_id="id",
                google_client_secret="secret",  # pragma: allowlist secret
                google_redirect_uri="https://example.test/api/v1/auth/oauth/callback",
                frontend_url=None,
            ),
        ):
            result = capabilities.build_capabilities(email_enabled=False)

        assert result["auth"]["oauth"]["google"] is False

    def test_a_frontend_url_that_is_not_a_url_is_not_reported_as_available(self):
        with patch.object(
            capabilities,
            "get_settings",
            return_value=_settings(
                auth_jwt_enabled=True,
                auth_oauth_google_enabled=True,
                google_client_id="id",
                google_client_secret="secret",  # pragma: allowlist secret
                google_redirect_uri="https://example.test/api/v1/auth/oauth/callback",
                frontend_url="app.example.test",
            ),
        ):
            result = capabilities.build_capabilities(email_enabled=False)

        assert result["auth"]["oauth"]["google"] is False

    def test_a_provider_without_a_redirect_uri_is_not_reported_as_available(self):
        # The endpoint needs the redirect URI as well as the credentials:
        # without it the click answers 500 ("Google OAuth is not
        # configured"). The capability used to say "available" anyway, so the
        # interface offered a button that could only fail.
        with patch.object(
            capabilities,
            "get_settings",
            return_value=_settings(
                auth_jwt_enabled=True,
                auth_oauth_google_enabled=True,
                google_client_id="id",
                google_client_secret="secret",  # pragma: allowlist secret
                google_redirect_uri=None,
            ),
        ):
            result = capabilities.build_capabilities(email_enabled=False)

        assert result["auth"]["oauth"]["google"] is False

    def test_a_provider_is_not_reported_as_available_without_jwt(self):
        # The whole auth router - and with it the OAuth endpoints - is only
        # mounted when JWT is enabled. Without it the click answers 404.
        with patch.object(
            capabilities,
            "get_settings",
            return_value=_settings(
                auth_jwt_enabled=False,
                auth_oauth_google_enabled=True,
                google_client_id="id",
                google_client_secret="secret",  # pragma: allowlist secret
                google_redirect_uri="https://example.test/api/v1/auth/oauth/callback",
            ),
        ):
            result = capabilities.build_capabilities(email_enabled=False)

        assert result["auth"]["oauth"]["google"] is False

    def test_apple_needs_its_key_and_the_same_redirect_uri(self):
        # The Apple endpoint reads the private key from a file and reuses the
        # redirect URI setting, so a deployment without either is not a
        # deployment with a working Apple button.
        configured = _settings(
            auth_jwt_enabled=True,
            auth_oauth_apple_enabled=True,
            apple_client_id="id",
            apple_team_id="team",
            apple_private_key_path="/tmp/AppleAuthKey.p8",
            google_redirect_uri="https://example.test/api/v1/auth/oauth/callback",
            frontend_url="https://app.example.test",
        )
        with patch.object(capabilities, "get_settings", return_value=configured):
            result = capabilities.build_capabilities(email_enabled=False)
        assert result["auth"]["oauth"]["apple"] is True

        without_key = _settings(
            auth_jwt_enabled=True,
            auth_oauth_apple_enabled=True,
            apple_client_id="id",
            apple_team_id="team",
            apple_private_key_path=None,
            google_redirect_uri="https://example.test/api/v1/auth/oauth/callback",
            frontend_url="https://app.example.test",
        )
        with patch.object(capabilities, "get_settings", return_value=without_key):
            result = capabilities.build_capabilities(email_enabled=False)
        assert result["auth"]["oauth"]["apple"] is False

    def test_a_dummy_mail_service_is_reported_as_disabled(self):
        with patch.object(capabilities, "get_settings", return_value=_settings()):
            result = capabilities.build_capabilities(email_enabled=False)

        assert result["email"] == {"enabled": False, "provider": "dummy"}

    def test_a_configured_mail_service_is_reported_as_enabled(self):
        with patch.object(capabilities, "get_settings", return_value=_settings()):
            result = capabilities.build_capabilities(email_enabled=True)

        assert result["email"] == {"enabled": True, "provider": "smtp"}

    def test_error_tracking_follows_the_configured_dsn(self):
        with patch.object(capabilities, "get_settings", return_value=_settings()):
            assert (
                capabilities.build_capabilities(email_enabled=False)["observability"][
                    "error_tracking"
                ]
                is False
            )

        with patch.object(
            capabilities, "get_settings", return_value=_settings(sentry_dsn="https://key@sentry/1")
        ):
            assert (
                capabilities.build_capabilities(email_enabled=False)["observability"][
                    "error_tracking"
                ]
                is True
            )


class TestDemoFlags:
    """The demo flags are published split - the master flag said four things.

    The deployment that answers with a live model and holds a seeded
    catalogue is a real deployment, and the master flag said "demo mode"
    about it anyway.
    """

    def test_the_flag_that_answers_the_chat_is_the_one_that_is_published(self):
        with patch.object(capabilities, "get_settings", return_value=_settings(demo_llm_mode=True)):
            result = capabilities.build_capabilities(email_enabled=False)

        assert result["llm"]["demo_llm_mode"] is True
        assert result["llm"]["mode"] == "local-model"

    def test_a_deployment_with_a_real_model_does_not_read_as_a_demo(self):
        with patch.object(
            capabilities, "get_settings", return_value=_settings(demo_llm_mode=False)
        ):
            result = capabilities.build_capabilities(email_enabled=False)

        assert result["llm"]["demo_llm_mode"] is False
        assert result["llm"]["mode"] == "provider"

    def test_the_master_flag_is_not_published(self):
        # The master flag is the fallback of the four split flags, and it is
        # the fallback of the settings module - it is not a fact about the
        # deployment, so it is not published.
        with patch.object(capabilities, "get_settings", return_value=_settings(demo_mode=True)):
            result = capabilities.build_capabilities(email_enabled=False)

        assert "demo_mode" not in result["llm"]
        assert "demo_mode" not in result

    def test_the_catalogue_flag_is_published_under_data(self):
        with patch.object(
            capabilities, "get_settings", return_value=_settings(demo_data_mode=True)
        ):
            result = capabilities.build_capabilities(email_enabled=False)

        assert result["data"]["demo_data_mode"] is True

    def test_a_seeded_catalogue_is_told_apart_from_a_canned_model(self):
        # The two flags are independent: a deployment can seed its catalogue
        # and still answer with a real model.
        with patch.object(
            capabilities,
            "get_settings",
            return_value=_settings(demo_data_mode=True, demo_llm_mode=False),
        ):
            result = capabilities.build_capabilities(email_enabled=False)

        assert result["data"]["demo_data_mode"] is True
        assert result["llm"]["demo_llm_mode"] is False


class TestIngestCapabilities:
    """The interface must not offer a file the deployment cannot open."""

    def test_the_formats_the_chain_accepts_are_published(self):
        from services.property_import import SUPPORTED_SUFFIXES

        with patch.object(capabilities, "get_settings", return_value=_settings()):
            result = capabilities.build_capabilities(email_enabled=False)

        published = result["ingest"]["formats"]
        assert set(published) <= set(SUPPORTED_SUFFIXES)
        assert ".csv" in published

    def test_a_format_whose_reader_is_missing_is_not_offered(self, monkeypatch):
        # The reader of .xls and .ods is an extra: a deployment without it
        # fails at the read, so the interface must not offer the file.
        monkeypatch.setattr("data.excel_loader.reader_installed", lambda module: module != "xlrd")

        with patch.object(capabilities, "get_settings", return_value=_settings()):
            result = capabilities.build_capabilities(email_enabled=False)

        assert ".xls" not in result["ingest"]["formats"]
        assert ".csv" in result["ingest"]["formats"]

    def test_a_deployment_without_a_spreadsheet_reader_says_so(self, monkeypatch):
        monkeypatch.setattr("data.excel_loader.reader_installed", lambda _module: False)

        with patch.object(capabilities, "get_settings", return_value=_settings()):
            result = capabilities.build_capabilities(email_enabled=False)

        assert result["ingest"]["excel"] is False
        assert result["ingest"]["formats"] == [".csv"]

    def test_a_deployment_with_a_spreadsheet_reader_says_so(self, monkeypatch):
        # The readers of .xls and .ods are extras, so whether they are
        # installed is a fact of the environment and not of the endpoint:
        # the test says what the deployment reads instead of assuming that
        # the machine it runs on has every extra.
        monkeypatch.setattr("data.excel_loader.reader_installed", lambda _module: True)

        with patch.object(capabilities, "get_settings", return_value=_settings()):
            result = capabilities.build_capabilities(email_enabled=False)

        assert result["ingest"]["excel"] is True
        assert ".xls" in result["ingest"]["formats"]
        assert ".ods" in result["ingest"]["formats"]

    def test_a_format_the_chain_reads_with_the_csv_loader_is_published(self, monkeypatch):
        # The chain hands every format that is not a spreadsheet to the CSV
        # loader, so the endpoint publishes what the chain accepts - the
        # interface is never offered less than the deployment reads.
        import services.property_import as property_import

        monkeypatch.setattr(
            property_import,
            "SUPPORTED_SUFFIXES",
            property_import.SUPPORTED_SUFFIXES | {".tsv"},
        )

        with patch.object(capabilities, "get_settings", return_value=_settings()):
            result = capabilities.build_capabilities(email_enabled=False)

        assert ".tsv" in result["ingest"]["formats"]
        assert ".csv" in result["ingest"]["formats"]

    def test_the_register_is_published_as_a_source(self):
        # Whether the register can be read is a fact about the deployment's
        # own database, so the builder publishes the fact it is given.
        with patch.object(capabilities, "get_settings", return_value=_settings()):
            result = capabilities.build_capabilities(email_enabled=False, register=True)

        assert result["ingest"]["register"] is True

    def test_a_deployment_that_holds_no_register_does_not_publish_it(self):
        with patch.object(capabilities, "get_settings", return_value=_settings()):
            result = capabilities.build_capabilities(email_enabled=False, register=False)

        assert result["ingest"]["register"] is False

    def test_a_deployment_that_cannot_name_the_sources_reads_no_format(self, monkeypatch):
        # The endpoint is public and every page reads it, so a broken import
        # must not take the whole answer with it: the deployment says that
        # it reads no format. The register is a fact of its own - it was read
        # from the database, not from the formats - so it is published even
        # now.
        monkeypatch.setitem(sys.modules, "services.property_import", None)

        with patch.object(capabilities, "get_settings", return_value=_settings()):
            result = capabilities.build_capabilities(email_enabled=False, register=True)

        assert result["ingest"] == {"formats": [], "excel": False, "register": True}


class TestTheRegisterAnswer:
    """The answer about the register is kept, so the public endpoint does
    not read the database on every request."""

    @staticmethod
    def _counting_reader(monkeypatch, answer=True):
        """Replace the database read with one that counts the calls."""
        reads = []

        async def counted(session, city_norms, until=None):
            reads.append(list(city_norms))
            return answer

        monkeypatch.setattr(
            "db.property_transaction_repo.has_sales_of_cities",
            counted,
        )
        return reads

    @staticmethod
    def _clock(monkeypatch, step=1.0):
        """A clock the test holds still.

        The answer is kept for a minute and a failure is said out loud once a
        minute, so a test that reads the real clock is a test that waits.
        """
        state = {"now": 1000.0}

        def now():
            state["now"] += step
            return state["now"]

        monkeypatch.setattr(capabilities, "_now", now)
        return state

    @pytest.mark.asyncio
    async def test_the_register_is_read_once_and_kept(self, db_session, monkeypatch):
        reads = self._counting_reader(monkeypatch)

        first = await capabilities._register_readable(db_session)
        second = await capabilities._register_readable(db_session)

        assert first is True
        assert second is True
        assert len(reads) == 1

    @pytest.mark.asyncio
    async def test_the_answer_is_read_again_once_it_aged(self, db_session, monkeypatch):
        # The register changes when the ingest runs, so a kept answer must
        # not outlive the minute it was kept for.
        monkeypatch.setattr(capabilities, "REGISTER_CACHE_SECONDS", 0.0)
        reads = self._counting_reader(monkeypatch)

        await capabilities._register_readable(db_session)
        await capabilities._register_readable(db_session)

        assert len(reads) == 2

    @pytest.mark.asyncio
    async def test_a_deployment_without_the_register_keeps_that_answer(
        self, db_session, monkeypatch
    ):
        reads = self._counting_reader(monkeypatch, answer=False)

        first = await capabilities._register_readable(db_session)
        second = await capabilities._register_readable(db_session)

        assert first is False
        assert second is False
        assert len(reads) == 1

    @pytest.mark.asyncio
    async def test_an_answer_is_kept_for_the_minute(self, db_session, monkeypatch):
        # The register changes when the ingest runs, which is rare: an answer
        # that was given is kept for a minute.
        self._clock(monkeypatch, step=10.0)
        reads = self._counting_reader(monkeypatch)

        await capabilities._register_readable(db_session)
        await capabilities._register_readable(db_session)

        assert len(reads) == 1

    @pytest.mark.asyncio
    async def test_a_failure_is_asked_again_sooner_than_an_answer(self, db_session, monkeypatch):
        # A failure is not an answer: the database may be back in a moment,
        # and a deployment that came back must be seen at once.
        self._clock(monkeypatch, step=10.0)
        reads = []

        async def failing(session, city_norms, until=None):
            reads.append(list(city_norms))
            raise RuntimeError("the database is away")

        monkeypatch.setattr(
            "db.property_transaction_repo.has_sales_of_cities",
            failing,
        )

        await capabilities._register_readable(db_session)
        await capabilities._register_readable(db_session)

        assert len(reads) == 2

    @pytest.mark.asyncio
    async def test_a_failed_read_publishes_the_unknown_answer(self, db_session, monkeypatch):
        # A database that is away says nothing about what the deployment
        # holds: the answer of a moment ago is not an answer about the
        # deployment now. The unknown one is published instead.
        monkeypatch.setattr(capabilities, "REGISTER_CACHE_SECONDS", 0.0)
        calls = []

        async def failing_after_the_first(session, city_norms, until=None):
            calls.append(list(city_norms))
            if len(calls) == 1:
                return True
            raise RuntimeError("the database is away")

        monkeypatch.setattr(
            "db.property_transaction_repo.has_sales_of_cities",
            failing_after_the_first,
        )

        first = await capabilities._register_readable(db_session)
        second = await capabilities._register_readable(db_session)

        assert first is True
        assert second is None
        assert len(calls) == 2

    @pytest.mark.asyncio
    async def test_a_failed_read_without_a_previous_answer_says_nothing(
        self, db_session, monkeypatch
    ):
        # A deployment that could not be asked is not a deployment that holds
        # no register: the two are different facts, and the endpoint
        # publishes both - as None and as False.
        async def failing(session, city_norms, until=None):
            raise RuntimeError("the database is away")

        monkeypatch.setattr(
            "db.property_transaction_repo.has_sales_of_cities",
            failing,
        )

        assert await capabilities._register_readable(db_session) is None

    @pytest.mark.asyncio
    async def test_a_failure_is_kept_for_a_short_while(self, db_session, monkeypatch):
        # A database that stays away must not be asked on every request: the
        # failure is kept for a moment, and it is kept for a shorter while
        # than an answer, so a database that comes back is seen at once.
        self._clock(monkeypatch, step=1.0)
        reads = []

        async def failing(session, city_norms, until=None):
            reads.append(list(city_norms))
            raise RuntimeError("the database is away")

        monkeypatch.setattr(
            "db.property_transaction_repo.has_sales_of_cities",
            failing,
        )

        await capabilities._register_readable(db_session)
        await capabilities._register_readable(db_session)

        assert len(reads) == 1

    @pytest.mark.asyncio
    async def test_a_failed_read_leaves_the_session_usable(self, db_session, monkeypatch):
        # The read that failed leaves the session in a transaction that
        # cannot be committed: without the rollback the request would end in
        # a server error instead of in a degraded answer.
        async def failing(session, city_norms, until=None):
            await session.execute(text("SELECT * FROM a_table_that_is_not_there"))
            return True

        monkeypatch.setattr(
            "db.property_transaction_repo.has_sales_of_cities",
            failing,
        )

        assert await capabilities._register_readable(db_session) is None

        # The session is in order, so the rest of the request still runs.
        result = await db_session.execute(text("SELECT 1"))
        assert result.scalar() == 1

    @pytest.mark.asyncio
    async def test_a_failed_read_puts_the_transaction_back_in_order(self, db_session, monkeypatch):
        # The failed statement left the transaction unusable, and the session
        # is committed when the request ends: the rollback here is what keeps
        # the request from ending in a server error. The route writes nothing
        # of its own - the audit entry is written after the route - so the
        # rollback throws nothing away.
        async def failing(session, city_norms, until=None):
            raise RuntimeError("the database is away")

        monkeypatch.setattr(
            "db.property_transaction_repo.has_sales_of_cities",
            failing,
        )

        await db_session.execute(text("SELECT 1"))
        assert db_session.in_transaction()

        assert await capabilities._register_readable(db_session) is None

        assert not db_session.in_transaction()

    @pytest.mark.asyncio
    async def test_a_read_that_failed_before_the_question_leaves_the_session_usable(
        self, db_session, monkeypatch
    ):
        # The read can fail before the question is even asked - the place
        # that names the cities is not there. The request still ends in an
        # answer, and the answer is the unknown one: the deployment has not
        # said that it holds no register, it has not said anything.
        monkeypatch.setitem(sys.modules, "data.places", None)

        answer = await capabilities._register_readable(db_session)

        assert answer is None
        result = await db_session.execute(text("SELECT 1"))
        assert result.scalar_one() == 1

    @pytest.mark.asyncio
    async def test_the_unknown_answer_is_published_as_it_is(self, db_session, monkeypatch):
        # The payload says that the register is unknown, not that the
        # deployment holds none.
        async def failing(session, city_norms, until=None):
            raise RuntimeError("the database is away")

        monkeypatch.setattr(
            "db.property_transaction_repo.has_sales_of_cities",
            failing,
        )

        # The answer is read first and published second: a payload that is
        # handed the unknown one proves nothing about the read.
        answer = await capabilities._register_readable(db_session)

        with patch.object(capabilities, "get_settings", return_value=_settings()):
            result = capabilities.build_capabilities(email_enabled=False, register=answer)

        assert answer is None
        assert result["ingest"]["register"] is None

    @pytest.mark.asyncio
    async def test_a_failure_that_stays_is_said_out_loud_again(
        self, db_session, monkeypatch, caplog
    ):
        # The endpoint is public and every page reads it: a warning per
        # request would flood the log, and a warning once per process would
        # hide a database that stays away.
        async def failing(session, city_norms, until=None):
            raise RuntimeError("the database is away")

        monkeypatch.setattr(
            "db.property_transaction_repo.has_sales_of_cities",
            failing,
        )
        self._clock(monkeypatch)
        monkeypatch.setattr(capabilities, "REGISTER_WARNING_SECONDS", 0.0)
        # The answer is read again only once the failure window is over, so
        # the failure is let go of here: the question is what is said when
        # the same failure comes round a second time.
        monkeypatch.setattr(capabilities, "REGISTER_FAILURE_CACHE_SECONDS", 0.0)

        with caplog.at_level("WARNING", logger="api.routers.capabilities"):
            await capabilities._register_readable(db_session)
            await capabilities._register_readable(db_session)

        said = [
            record for record in caplog.records if "register could not be read" in record.message
        ]
        assert len(said) == 2

    @pytest.mark.asyncio
    async def test_a_failure_is_not_said_twice_in_the_same_minute(
        self, db_session, monkeypatch, caplog
    ):
        async def failing(session, city_norms, until=None):
            raise RuntimeError("the database is away")

        monkeypatch.setattr(
            "db.property_transaction_repo.has_sales_of_cities",
            failing,
        )
        self._clock(monkeypatch)
        # The answer is read again only once the failure window is over, so
        # the failure is let go of here: the question is what is said when
        # the same failure comes round a second time inside the same minute.
        monkeypatch.setattr(capabilities, "REGISTER_FAILURE_CACHE_SECONDS", 0.0)

        with caplog.at_level("WARNING", logger="api.routers.capabilities"):
            await capabilities._register_readable(db_session)
            await capabilities._register_readable(db_session)

        said = [
            record for record in caplog.records if "register could not be read" in record.message
        ]
        assert len(said) == 1


class TestCapabilitiesEndpoint:
    """The endpoint reads the mail state the startup recorded."""

    @pytest.mark.asyncio
    async def test_endpoint_reports_the_startup_mail_state(self, capabilities_client):
        with patch.object(capabilities, "get_settings", return_value=_settings()):
            response = await capabilities_client.get("/api/v1/capabilities")

        assert response.status_code == 200
        body = response.json()
        assert body["email"]["enabled"] is False
        assert body["auth"]["oauth"]["google"] is False
        assert "llm" in body
        assert "observability" in body
        assert body["llm"]["demo_llm_mode"] is False
        assert body["data"]["demo_data_mode"] is False
        assert body["ingest"]["formats"]
        # The spreadsheet answer follows the formats: it says that the
        # deployment reads a spreadsheet, and whether the optional readers
        # are installed is a fact of the environment and not of the
        # endpoint.
        assert body["ingest"]["excel"] is bool(
            set(body["ingest"]["formats"]) & {".xlsx", ".xls", ".ods"}
        )
        # The register is read from the sales the ingest stored, and this
        # deployment stored none: it holds no register.
        assert body["ingest"]["register"] is False

    @pytest.mark.asyncio
    async def test_endpoint_needs_no_api_key(self, capabilities_client):
        with patch.object(capabilities, "get_settings", return_value=_settings()):
            response = await capabilities_client.get("/api/v1/capabilities")

        assert response.status_code == 200


class TestBuildMetadata:
    """The build is published to a privileged caller and to nobody else."""

    @pytest.mark.asyncio
    async def test_an_ordinary_caller_is_told_nothing_about_the_build(
        self, capabilities_client, monkeypatch
    ):
        monkeypatch.setenv("BUILD_SHA", "abc123")
        monkeypatch.delenv("ADMIN_EMAILS", raising=False)
        monkeypatch.delenv("ADMIN_IPS", raising=False)

        with patch.object(capabilities, "get_settings", return_value=_settings()):
            response = await capabilities_client.get("/api/v1/capabilities")

        assert response.status_code == 200
        assert "build" not in response.json()

    @pytest.mark.asyncio
    async def test_a_listed_address_is_told_which_build_it_is_talking_to(
        self, capabilities_client, monkeypatch
    ):
        monkeypatch.setenv("ADMIN_IPS", "203.0.113.7")
        monkeypatch.setenv("BUILD_SHA", "abc123")
        monkeypatch.setenv("BUILD_AT", "2026-11-11T02:00:00Z")
        monkeypatch.setenv("DEPLOY_RUN_ID", "4242")
        monkeypatch.setenv("BUILD_REPO", "someone/some-repo")

        with patch.object(capabilities, "get_settings", return_value=_settings()):
            response = await capabilities_client.get(
                "/api/v1/capabilities", headers={"x-forwarded-for": "203.0.113.7"}
            )

        assert response.status_code == 200
        build = response.json()["build"]
        assert build["sha"] == "abc123"
        assert build["built_at"] == "11.11.2026 02:00"
        assert build["deploy_run_id"] == "4242"
        assert build["commit_url"].endswith("/some-repo/commit/abc123")
        assert build["deploy_url"].endswith("/some-repo/actions/runs/4242")

    @pytest.mark.asyncio
    async def test_an_address_that_is_not_on_the_list_is_told_nothing(
        self, capabilities_client, monkeypatch
    ):
        monkeypatch.setenv("ADMIN_IPS", "203.0.113.7")
        monkeypatch.setenv("BUILD_SHA", "abc123")

        with patch.object(capabilities, "get_settings", return_value=_settings()):
            response = await capabilities_client.get(
                "/api/v1/capabilities", headers={"x-forwarded-for": "198.51.100.4"}
            )

        assert response.status_code == 200
        assert "build" not in response.json()

    @pytest.mark.asyncio
    async def test_a_privileged_caller_without_a_build_is_told_no_build(
        self, capabilities_client, monkeypatch
    ):
        # The list is there, the deployment does not say which build it runs:
        # there is nothing to show, and nothing broken.
        monkeypatch.setenv("ADMIN_IPS", "203.0.113.7")
        for name in ("BUILD_SHA", "BUILD_AT", "DEPLOY_RUN_ID"):
            monkeypatch.delenv(name, raising=False)

        with patch.object(capabilities, "get_settings", return_value=_settings()):
            response = await capabilities_client.get(
                "/api/v1/capabilities", headers={"x-forwarded-for": "203.0.113.7"}
            )

        assert response.status_code == 200
        assert "build" not in response.json()

    @pytest.mark.asyncio
    async def test_an_unusable_token_does_not_break_the_endpoint(self, capabilities_client):
        # The endpoint is public and the landing page asks it on every visit.
        # A stale cookie must not turn it into a 401.
        with patch.object(capabilities, "get_settings", return_value=_settings()):
            response = await capabilities_client.get(
                "/api/v1/capabilities", cookies={"access_token": "not-a-token"}
            )

        assert response.status_code == 200

    def test_the_builder_leaves_the_build_out_when_there_is_none(self):
        with patch.object(capabilities, "get_settings", return_value=_settings()):
            result = capabilities.build_capabilities(email_enabled=False)

        assert "build" not in result

    def test_the_builder_publishes_the_build_it_is_given(self):
        with patch.object(capabilities, "get_settings", return_value=_settings()):
            result = capabilities.build_capabilities(email_enabled=False, build={"sha": "abc123"})

        assert result["build"] == {"sha": "abc123"}


class TestTheRegisterReadFromTheDatabase:
    """The endpoint reads the register the way a deployment reads it.

    Nothing is patched here: the answer comes from the sales the ingest
    stored, so the test proves that the endpoint and the database agree.
    """

    @pytest.mark.asyncio
    async def test_a_deployment_that_stored_no_sale_holds_no_register(self, db_session):
        answer = await capabilities._register_readable(db_session)

        assert answer is False

    @pytest.mark.asyncio
    async def test_a_deployment_that_stored_a_sale_holds_the_register(self, db_session):
        place = next(place for place in PLACES if place.register_city)
        db_session.add(
            PropertyTransaction(
                external_id=f"rcn-{place.name}",
                transaction_id=f"deed-{place.name}",
                city=place.register_city,
                city_norm=normalize_text(place.register_city),
                street="Floryanska",
                street_norm=normalize_text("Floryanska"),
                area_sqm=50.0,
                price_brutto=500000.0,
                transaction_date=date(2024, 5, 1),
            )
        )
        await db_session.commit()

        answer = await capabilities._register_readable(db_session)

        assert answer is True
