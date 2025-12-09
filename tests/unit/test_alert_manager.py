import tempfile
from pathlib import Path
from unittest.mock import patch

from notifications.alert_manager import AlertManager
from notifications.email_service import EmailService, EmailConfig, EmailProvider
from data.schemas import Property, PropertyCollection, PropertyType
from utils.saved_searches import SavedSearch


def make_prop(pid, city, price, rooms, area=50):
    return Property(
        id=pid,
        city=city,
        price=price,
        rooms=rooms,
        bathrooms=1,
        area_sqm=area,
        property_type=PropertyType.APARTMENT,
        has_parking=True,
        is_furnished=True,
    )


def make_email_service():
    return EmailService(EmailConfig(
        provider=EmailProvider.GMAIL,
        smtp_server="smtp.gmail.com",
        smtp_port=587,
        username="u@example.com",
        password="pw",
        from_email="u@example.com",
    ))


def test_check_price_drops_and_send(tmp_path):
    svc = make_email_service()
    am = AlertManager(svc, storage_path=str(tmp_path))

    prev = PropertyCollection(properties=[make_prop("p1", "Krakow", 1000, 2)], total_count=1)
    curr = PropertyCollection(properties=[make_prop("p1", "Krakow", 900, 2)], total_count=1)
    drops = am.check_price_drops(curr, prev, threshold_percent=5.0)
    assert len(drops) == 1 and drops[0]["savings"] == 100

    with patch.object(EmailService, "send_email", return_value=True):
        ok = am.send_price_drop_alert("user@example.com", drops[0], send_email=True)
        assert ok is True
        stats = am.get_alert_statistics()
        assert stats["total_sent"] >= 1

    # Duplicate should not send again
    with patch.object(EmailService, "send_email", return_value=True):
        ok2 = am.send_price_drop_alert("user@example.com", drops[0], send_email=True)
        assert ok2 is False


def test_check_new_property_matches_and_send(tmp_path):
    svc = make_email_service()
    am = AlertManager(svc, storage_path=str(tmp_path))

    props = PropertyCollection(properties=[
        make_prop("p1", "Krakow", 900, 2),
        make_prop("p2", "Krakow", 1200, 3),
    ], total_count=2)

    ss = SavedSearch(id="s1", name="Krakow Budget", city="Krakow", max_price=1000)
    matches = am.check_new_property_matches(props, [ss])
    assert "s1" in matches and len(matches["s1"]) == 1

    with patch.object(EmailService, "send_email", return_value=True):
        ok = am.send_new_property_alerts("user@example.com", "s1", ss.name, matches["s1"], send_email=True)
        assert ok is True


def test_get_property_key_stable():
    svc = make_email_service()
    am = AlertManager(svc)
    p = make_prop(None, "Krakow", 900, 2, area=60)
    k1 = am._get_property_key(p)
    p2 = make_prop(None, "Krakow", 850, 2, area=60)
    k2 = am._get_property_key(p2)
    assert k1 == k2

