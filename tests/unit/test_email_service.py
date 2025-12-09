import pytest
from unittest.mock import patch

from notifications.email_service import (
    EmailService,
    EmailConfig,
    EmailProvider,
    EmailServiceFactory,
    EmailValidationError,
)


def make_config(provider=EmailProvider.GMAIL):
    return EmailConfig(
        provider=provider,
        smtp_server="smtp.gmail.com" if provider == EmailProvider.GMAIL else "smtp-mail.outlook.com",
        smtp_port=587,
        username="test@example.com",
        password="password",
        from_email="test@example.com",
        from_name="Tester",
        use_tls=True,
        use_ssl=False,
        timeout=5,
    )


def test_validate_email():
    svc = EmailService(make_config())
    assert svc.validate_email("user@example.com")
    assert svc.validate_email("user.name+tag@example.co.uk")
    assert not svc.validate_email("invalid")
    assert not svc.validate_email("user@")
    assert not svc.validate_email("@example.com")


def test_factories_create_services():
    g = EmailServiceFactory.create_gmail_service("u@gmail.com", "app_pw")
    assert isinstance(g, EmailService)
    assert g.config.provider == EmailProvider.GMAIL
    o = EmailServiceFactory.create_outlook_service("u@outlook.com", "pw")
    assert isinstance(o, EmailService)
    assert o.config.provider == EmailProvider.OUTLOOK


def test_send_email_success_and_stats():
    svc = EmailService(make_config())
    with patch.object(EmailService, "_send_message", return_value=None):
        ok = svc.send_email("user@example.com", "Subj", "Body", html=False)
        assert ok is True
        stats = svc.get_statistics()
        assert stats["sent"] == 1 and stats["failed"] == 0


def test_send_email_invalid_raises():
    svc = EmailService(make_config())
    with pytest.raises(EmailValidationError):
        svc.send_email("bad", "s", "b")


def test_send_bulk_emails_counts():
    svc = EmailService(make_config())
    with patch.object(EmailService, "_send_message", return_value=None):
        res = svc.send_bulk_emails(["a@example.com", "b@example.com"], "s", "b", html=False, batch_size=1)
        assert res["sent"] == 2 and res["failed"] == 0

