"""The operator's notification for a new lead capture.

The landing's waitlist and the footer's form both post to
``POST /api/v1/leads/visitor`` and the row lands in the lead board. Until
TaskMaster #108 the row was the END of the story: nothing told the operator
that a capture had arrived, so a launch had to be followed by a human reading
the board.

This module is the producer. It renders the high-value-lead template that
already exists and sends ONE message to the operator's address. The address
comes from the environment (``LEAD_ALERT_EMAIL_TO``), never from the source:
an address in the code is an address that cannot be changed without a release,
and the repository holds a test that forbids exactly that
(``test_no_hardcoded_privileged_list``).

The send is best-effort by design. A broken mail transport must never take the
capture down: the lead row is written first, and a failed send is logged.
"""

import logging
import os
import threading
import time
from collections import deque
from typing import Any, Optional

from core.security_utils import sanitize_for_log
from notifications.email_service import EmailService
from notifications.email_templates import HighValueLeadTemplate

logger = logging.getLogger(__name__)

# The operator's address. Unset means the deployment wants no lead alerts.
LEAD_ALERT_EMAIL_TO_ENV = "LEAD_ALERT_EMAIL_TO"

# How many alerts may leave the deployment in an hour. The capture endpoint
# is public and the API rate limiter allows far more requests per minute than
# a waitlist receives signups, so without a budget a scripted client could
# fill the operator's mailbox. The budget bounds the MAIL, not the capture:
# every lead is still stored, and the board still shows it.
ALERT_BUDGET_PER_HOUR_ENV = "LEAD_ALERT_BUDGET_PER_HOUR"
ALERT_BUDGET_PER_HOUR_DEFAULT = 30
_ALERT_WINDOW_SECONDS = 3600

_alert_lock = threading.Lock()
_alert_times: deque[float] = deque()


def lead_alert_recipient() -> Optional[str]:
    """Return the operator's address, or ``None`` when alerts are off."""
    return os.getenv(LEAD_ALERT_EMAIL_TO_ENV, "").strip() or None


def alert_budget_per_hour() -> int:
    """How many alerts may leave the deployment in an hour."""
    raw = os.getenv(ALERT_BUDGET_PER_HOUR_ENV, "").strip()
    if raw.isdigit():
        return int(raw)
    return ALERT_BUDGET_PER_HOUR_DEFAULT


def _within_alert_budget() -> bool:
    """Whether another alert fits in the hourly budget."""
    now = time.monotonic()
    with _alert_lock:
        while _alert_times and now - _alert_times[0] > _ALERT_WINDOW_SECONDS:
            _alert_times.popleft()
        if len(_alert_times) >= alert_budget_per_hour():
            return False
        _alert_times.append(now)
        return True


def build_lead_alert_payload(lead: Any) -> dict[str, Any]:
    """Return the template's view of a lead.

    The template reads its values with ``.get``, so every key is optional; the
    ones that are missing here are simply absent from the mail.
    """
    last_activity = getattr(lead, "last_activity_at", None)
    return {
        "name": getattr(lead, "name", None) or "Anonymous lead",
        "email": getattr(lead, "email", None) or "",
        "phone": getattr(lead, "phone", None) or "",
        "score": getattr(lead, "current_score", 0) or 0,
        "source": getattr(lead, "source", None) or "website",
        "interactions": 0,
        "last_activity": (
            last_activity.strftime("%Y-%m-%d %H:%M UTC") if last_activity else "just now"
        ),
    }


def send_lead_alert(lead: Any, email_service: EmailService, recipient: str) -> bool:
    """Send one alert about ``lead`` to ``recipient``.

    Returns ``True`` when the message went out, ``False`` when the hourly
    budget was spent (the capture is stored either way). Raises
    ``EmailSendError`` when the transport refused the message - the caller
    decides what that means.
    """
    if not _within_alert_budget():
        logger.warning(
            "Lead alert skipped: the hourly budget of %s is spent",
            alert_budget_per_hour(),
        )
        return False

    subject, body = HighValueLeadTemplate.render(build_lead_alert_payload(lead))
    email_service.send_email(recipient, subject, body, html=True)
    logger.info("Lead alert sent: source=%s", sanitize_for_log(getattr(lead, "source", None)))
    return True
