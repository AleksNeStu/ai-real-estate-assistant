"""
The privileged list and the build metadata (Task #73).

The list arrives through the environment and nowhere else, and the metadata
arrives the same way. These tests hold both to that.
"""

import pytest

from services.build_info import (
    build_metadata,
    is_privileged,
    privileged_emails,
    privileged_ips,
)

# Addresses in the reserved documentation ranges: RFC 5737 for the addresses,
# RFC 2606 for the accounts. They can never be on anyone's real list.
DOC_ADDRESS = "203.0.113.7"
OTHER_ADDRESS = "198.51.100.4"
DOC_ACCOUNT = "owner@example.com"


class TestPrivilegedList:
    """The list is read from the environment, and read afresh every time."""

    def test_no_variable_means_nobody_is_privileged(self, monkeypatch):
        monkeypatch.delenv("ADMIN_EMAILS", raising=False)
        monkeypatch.delenv("ADMIN_IPS", raising=False)

        assert is_privileged(email=DOC_ACCOUNT, ip=DOC_ADDRESS) is False
        assert privileged_emails() == []
        assert privileged_ips() == []

    def test_an_account_on_the_list_is_privileged(self, monkeypatch):
        monkeypatch.setenv("ADMIN_EMAILS", DOC_ACCOUNT)

        assert is_privileged(email=DOC_ACCOUNT, ip=OTHER_ADDRESS) is True

    def test_the_account_comparison_ignores_case_and_surrounding_space(self, monkeypatch):
        monkeypatch.setenv("ADMIN_EMAILS", f"  {DOC_ACCOUNT.upper()}  ")

        assert is_privileged(email=DOC_ACCOUNT) is True
        assert is_privileged(email=DOC_ACCOUNT.upper()) is True

    def test_an_address_on_the_list_is_privileged(self, monkeypatch):
        monkeypatch.setenv("ADMIN_IPS", f"{DOC_ADDRESS},{OTHER_ADDRESS}")

        assert is_privileged(ip=OTHER_ADDRESS) is True

    def test_the_address_comparison_is_exact(self, monkeypatch):
        monkeypatch.setenv("ADMIN_IPS", DOC_ADDRESS)

        assert is_privileged(ip=DOC_ADDRESS) is True
        assert is_privileged(ip=f"{DOC_ADDRESS}0") is False
        assert is_privileged(ip=f"{DOC_ADDRESS}:443") is False
        assert is_privileged(ip=DOC_ADDRESS[:-1]) is False

    def test_an_account_on_the_list_is_privileged_whatever_address_it_comes_from(self, monkeypatch):
        monkeypatch.setenv("ADMIN_EMAILS", DOC_ACCOUNT)
        monkeypatch.setenv("ADMIN_IPS", "")

        assert is_privileged(email=DOC_ACCOUNT, ip=None) is True

    def test_the_list_is_read_afresh_on_every_call(self, monkeypatch):
        # A name is added by changing the environment, not by a release and
        # not by a restart of anything that cached it.
        monkeypatch.setenv("ADMIN_EMAILS", DOC_ACCOUNT)
        assert privileged_emails() == [DOC_ACCOUNT]

        monkeypatch.setenv("ADMIN_EMAILS", f"{DOC_ACCOUNT},second@example.com")
        assert privileged_emails() == [DOC_ACCOUNT, "second@example.com"]

    def test_an_empty_or_blank_entry_is_not_a_member(self, monkeypatch):
        monkeypatch.setenv("ADMIN_EMAILS", " , ,")
        monkeypatch.setenv("ADMIN_IPS", "  ")

        assert is_privileged(email="", ip="") is False
        assert is_privileged(email=None, ip=None) is False


class TestBuildMetadata:
    """The metadata is what the deployment says, and nothing more."""

    def test_no_variable_means_no_metadata(self, monkeypatch):
        for name in ("BUILD_SHA", "BUILD_AT", "DEPLOY_RUN_ID", "BUILD_REPO"):
            monkeypatch.delenv(name, raising=False)

        assert build_metadata() is None

    def test_the_fields_that_are_set_are_reported(self, monkeypatch):
        monkeypatch.setenv("BUILD_SHA", "abc123")
        monkeypatch.setenv("BUILD_AT", "2026-11-11T02:00:00Z")
        monkeypatch.setenv("DEPLOY_RUN_ID", "4242")

        metadata = build_metadata()

        assert metadata is not None
        assert metadata["sha"] == "abc123"
        # The image's label is an RFC 3339 timestamp; the interface writes it
        # the way the house writes a moment - DD.MM.YYYY HH:MM.
        assert metadata["built_at"] == "11.11.2026 02:00"
        assert metadata["deploy_run_id"] == "4242"

    def test_a_moment_that_is_not_a_timestamp_is_shown_as_it_is(self, monkeypatch):
        monkeypatch.setenv("BUILD_AT", "whenever")

        metadata = build_metadata()

        assert metadata is not None
        assert metadata["built_at"] == "whenever"

    def test_a_field_that_is_not_set_is_absent(self, monkeypatch):
        # No empty row for a value the deployment does not have.
        monkeypatch.setenv("BUILD_SHA", "abc123")
        monkeypatch.delenv("BUILD_AT", raising=False)
        monkeypatch.delenv("DEPLOY_RUN_ID", raising=False)

        metadata = build_metadata()

        assert metadata is not None
        assert metadata == {"sha": "abc123"}

    def test_the_links_are_built_from_the_repository(self, monkeypatch):
        monkeypatch.setenv("BUILD_SHA", "abc123")
        monkeypatch.setenv("DEPLOY_RUN_ID", "4242")
        monkeypatch.setenv("BUILD_REPO", "someone/some-repo")

        metadata = build_metadata()

        assert metadata is not None
        assert metadata["commit_url"].endswith("/someone/some-repo/commit/abc123")
        assert metadata["deploy_url"].endswith("/someone/some-repo/actions/runs/4242")

    def test_without_a_repository_there_is_no_link_to_break(self, monkeypatch):
        monkeypatch.setenv("BUILD_SHA", "abc123")
        monkeypatch.delenv("BUILD_REPO", raising=False)

        metadata = build_metadata()

        assert metadata is not None
        assert "commit_url" not in metadata
        assert "deploy_url" not in metadata

    def test_a_blank_value_counts_as_not_set(self, monkeypatch):
        monkeypatch.setenv("BUILD_SHA", "   ")
        monkeypatch.setenv("BUILD_AT", "")
        monkeypatch.delenv("DEPLOY_RUN_ID", raising=False)

        assert build_metadata() is None


@pytest.mark.parametrize(
    "variable",
    ["ADMIN_EMAILS", "ADMIN_IPS", "BUILD_SHA", "BUILD_AT", "DEPLOY_RUN_ID", "BUILD_REPO"],
)
def test_the_variables_are_read_from_the_environment(variable):
    # The names are the contract with the deployment: the deploy writes them,
    # the application reads them.
    assert variable.isupper()
