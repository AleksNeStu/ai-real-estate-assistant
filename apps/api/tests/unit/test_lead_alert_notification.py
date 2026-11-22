"""The operator hears about a capture.

The waitlist form and the footer's form both post to
``POST /api/v1/leads/visitor``. The row that lands there used to be the end of
the story: nothing told the operator a signup had arrived, so a launch had to
be followed by a human reading the board (TaskMaster #108).

These tests hold the producer to its contract:

* ONE message per NEW capture, to the operator's address;
* no message for a capture that is not new (the same visitor again);
* no message when there is no transport, or no recipient;
* a mail that fails does NOT fail the capture.
"""

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from api.routers import leads
from db.database import get_db
from db.models import Lead
from notifications.lead_alerts import lead_alert_recipient


class RecordingEmailService:
    """A transport that remembers what it was asked to send."""

    def __init__(self, fail: bool = False) -> None:
        self.sent: list[dict] = []
        self.fail = fail

    def send_email(self, to_email, subject, body, html=False, cc=None, bcc=None):
        if self.fail:
            raise RuntimeError("transport refused the message")
        self.sent.append({"to": to_email, "subject": subject, "body": body, "html": html})
        return True


def _app(session, email_service=None, email_enabled: bool = True) -> FastAPI:
    app = FastAPI()
    app.include_router(leads.router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: session
    app.state.email_enabled = email_enabled
    app.state.email_service = email_service
    return app


class TestTheOperatorIsTold:
    """A new capture reaches the operator's mailbox."""

    async def test_a_new_capture_sends_one_message_to_the_operator(self, db_session, monkeypatch):
        monkeypatch.setenv("LEAD_ALERT_EMAIL_TO", "ops@example.com")
        email_service = RecordingEmailService()

        app = _app(db_session, email_service)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/leads/visitor",
                json={
                    "visitor_id": "visitor-alert-1",
                    "email": "waitlist@example.com",
                    "source": "propvector_waitlist",
                    "consent_given": True,
                },
            )

        assert response.status_code == 201, response.text
        assert len(email_service.sent) == 1, email_service.sent
        message = email_service.sent[0]
        assert message["to"] == "ops@example.com"
        assert "waitlist@example.com" in message["body"]

    async def test_the_same_visitor_again_does_not_send_a_second_message(
        self, db_session, monkeypatch
    ):
        """The endpoint is called on every page view by some clients."""
        monkeypatch.setenv("LEAD_ALERT_EMAIL_TO", "ops@example.com")
        email_service = RecordingEmailService()

        app = _app(db_session, email_service)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            for _ in range(2):
                response = await client.post(
                    "/api/v1/leads/visitor",
                    json={
                        "visitor_id": "visitor-alert-2",
                        "email": "twice@example.com",
                        "source": "propvector_waitlist",
                        "consent_given": True,
                    },
                )
                assert response.status_code == 201, response.text

        assert len(email_service.sent) == 1, email_service.sent

    async def test_a_capture_without_an_address_is_not_announced(self, db_session, monkeypatch):
        """There is no address to answer to, so there is nothing to announce."""
        monkeypatch.setenv("LEAD_ALERT_EMAIL_TO", "ops@example.com")
        email_service = RecordingEmailService()

        app = _app(db_session, email_service)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/leads/visitor",
                json={"visitor_id": "visitor-alert-3", "source": "organic"},
            )

        assert response.status_code == 201, response.text
        assert email_service.sent == []


class TestTheGuardrails:
    """Nothing is sent when nothing is configured, and a failure is not fatal."""

    async def test_no_transport_means_no_mail(self, db_session, monkeypatch):
        monkeypatch.setenv("LEAD_ALERT_EMAIL_TO", "ops@example.com")
        email_service = RecordingEmailService()

        app = _app(db_session, email_service, email_enabled=False)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/leads/visitor",
                json={
                    "visitor_id": "visitor-alert-4",
                    "email": "notransport@example.com",
                    "source": "propvector_waitlist",
                    "consent_given": True,
                },
            )

        assert response.status_code == 201, response.text
        assert email_service.sent == []

    async def test_no_recipient_means_no_mail(self, db_session, monkeypatch):
        monkeypatch.delenv("LEAD_ALERT_EMAIL_TO", raising=False)
        email_service = RecordingEmailService()

        app = _app(db_session, email_service)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/leads/visitor",
                json={
                    "visitor_id": "visitor-alert-5",
                    "email": "norecipient@example.com",
                    "source": "propvector_waitlist",
                    "consent_given": True,
                },
            )

        assert response.status_code == 201, response.text
        assert email_service.sent == []

    async def test_a_failing_mail_does_not_fail_the_capture(self, db_session, monkeypatch):
        """The visitor's address was saved. A broken transport cannot unsave it."""
        monkeypatch.setenv("LEAD_ALERT_EMAIL_TO", "ops@example.com")
        email_service = RecordingEmailService(fail=True)

        app = _app(db_session, email_service)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/leads/visitor",
                json={
                    "visitor_id": "visitor-alert-6",
                    "email": "broken@example.com",
                    "source": "propvector_waitlist",
                    "consent_given": True,
                },
            )

        assert response.status_code == 201, response.text
        stored = (
            await db_session.execute(select(Lead).where(Lead.visitor_id == "visitor-alert-6"))
        ).scalar_one()
        assert stored.email == "broken@example.com"


class TestTheBudget:
    """The capture endpoint is public, so the MAIL is bounded."""

    async def test_the_budget_bounds_the_mail_and_not_the_capture(self, db_session, monkeypatch):
        from notifications import lead_alerts

        monkeypatch.setenv("LEAD_ALERT_EMAIL_TO", "ops@example.com")
        monkeypatch.setenv("LEAD_ALERT_BUDGET_PER_HOUR", "1")
        with lead_alerts._alert_lock:
            lead_alerts._alert_times.clear()

        email_service = RecordingEmailService()
        app = _app(db_session, email_service)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            first = await client.post(
                "/api/v1/leads/visitor",
                json={
                    "visitor_id": "visitor-budget-1",
                    "email": "first@example.com",
                    "source": "propvector_waitlist",
                    "consent_given": True,
                },
            )
            second = await client.post(
                "/api/v1/leads/visitor",
                json={
                    "visitor_id": "visitor-budget-2",
                    "email": "second@example.com",
                    "source": "propvector_waitlist",
                    "consent_given": True,
                },
            )

        assert first.status_code == 201, first.text
        assert second.status_code == 201, second.text
        # One message went out; the second capture was stored but not announced.
        assert len(email_service.sent) == 1, email_service.sent
        stored = (
            await db_session.execute(select(Lead).where(Lead.visitor_id == "visitor-budget-2"))
        ).scalar_one()
        assert stored.email == "second@example.com"


class TestTheRecipient:
    """The address comes from the environment, never from the source."""

    def test_it_is_read_from_the_environment(self, monkeypatch):
        monkeypatch.setenv("LEAD_ALERT_EMAIL_TO", "  ops@example.com  ")
        assert lead_alert_recipient() == "ops@example.com"

    def test_an_unset_variable_means_no_recipient(self, monkeypatch):
        monkeypatch.delenv("LEAD_ALERT_EMAIL_TO", raising=False)
        assert lead_alert_recipient() is None

    def test_an_empty_variable_means_no_recipient(self, monkeypatch):
        monkeypatch.setenv("LEAD_ALERT_EMAIL_TO", "   ")
        assert lead_alert_recipient() is None
