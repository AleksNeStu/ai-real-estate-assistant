"""
Who may see the deployment's build metadata, and what that metadata is.

Two things live here, and both arrive through the ENVIRONMENT:

- The privileged list. The signed-in accounts (by e-mail) and the addresses
  (by IP) that may see which build they are talking to. ``ADMIN_EMAILS`` and
  ``ADMIN_IPS`` carry it. Adding a name is an environment change and never a
  release, and no address is written into the source, a fixture, a test, a
  snapshot or a document.

- The build metadata. The commit's sha, the build's date and time, the
  deploy's run id and the repository they belong to. ``BUILD_SHA``,
  ``BUILD_AT``, ``DEPLOY_RUN_ID`` and ``BUILD_REPO`` carry it.

Nothing here raises and nothing here logs. A deployment without the
variables has no privileged viewer and no build metadata, and the interface
shows its ordinary footer.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Optional

ADMIN_EMAILS_ENV = "ADMIN_EMAILS"
ADMIN_IPS_ENV = "ADMIN_IPS"
BUILD_SHA_ENV = "BUILD_SHA"
BUILD_AT_ENV = "BUILD_AT"
DEPLOY_RUN_ID_ENV = "DEPLOY_RUN_ID"
BUILD_REPO_ENV = "BUILD_REPO"


def _entries(raw: Optional[str]) -> list[str]:
    """Split a comma-separated environment value into its entries."""
    if not raw:
        return []
    return [entry.strip() for entry in raw.split(",") if entry.strip()]


def privileged_emails() -> list[str]:
    """The accounts on the list, lowercased - the comparison ignores case."""
    return [email.lower() for email in _entries(os.getenv(ADMIN_EMAILS_ENV))]


def privileged_ips() -> list[str]:
    """The addresses on the list. The comparison is exact."""
    return _entries(os.getenv(ADMIN_IPS_ENV))


def is_privileged(email: Optional[str] = None, ip: Optional[str] = None) -> bool:
    """Is this caller on the list?

    A signed-in account on the list is privileged whatever address it comes
    from, and an address on the list is privileged whoever is behind it.
    """
    if email and email.strip().lower() in privileged_emails():
        return True
    if ip and ip.strip() in privileged_ips():
        return True
    return False


def _built_at(raw: str) -> str:
    """The build's moment, in the house's own notation.

    The image's label is an RFC 3339 timestamp in UTC; the interface writes
    it the way the prototype writes it - ``DD.MM.YYYY HH:MM``, in the
    network's time. A value that is not a timestamp is passed through as it
    is: a deployment that sets it by hand still gets it shown.
    """
    if not raw:
        return raw
    text = raw.strip().replace("Z", "+00:00")
    try:
        moment = datetime.fromisoformat(text)
    except ValueError:
        return raw.strip()
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc).strftime("%d.%m.%Y %H:%M")


def build_metadata() -> Optional[dict[str, str]]:
    """The build this deployment is running, or None when it does not say.

    Only the fields that are actually set are returned, so the interface
    never renders an empty row for a value the deployment does not have.
    """
    values = {
        "sha": (os.getenv(BUILD_SHA_ENV) or "").strip(),
        "built_at": _built_at(os.getenv(BUILD_AT_ENV) or ""),
        "deploy_run_id": (os.getenv(DEPLOY_RUN_ID_ENV) or "").strip(),
    }
    repo = (os.getenv(BUILD_REPO_ENV) or "").strip()
    metadata = {key: value for key, value in values.items() if value}
    if not metadata:
        return None

    # The links are built here, not in the browser: the repository the sha
    # belongs to is part of the deployment's own configuration, and a browser
    # that has to guess it will guess wrong.
    if repo and metadata.get("sha"):
        metadata["commit_url"] = f"https://github.com/{repo}/commit/{metadata['sha']}"
    if repo and metadata.get("deploy_run_id"):
        metadata["deploy_url"] = (
            f"https://github.com/{repo}/actions/runs/{metadata['deploy_run_id']}"
        )
    return metadata
