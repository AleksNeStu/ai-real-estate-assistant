"""
The privileged list is never in the repository (Task #73).

The deployment tells the application which signed-in accounts and which
addresses may see the build it is running. The list arrives through the
environment - `ADMIN_EMAILS` and `ADMIN_IPS` - and nowhere else. Adding a
name is an environment change and never a release, and the repository never
carries a member of the list.

Two things are checked here, and both are about the files that could carry
the list:

1. No file ASSIGNS a value to `ADMIN_EMAILS` or `ADMIN_IPS`. A reference to
   the environment (`${ADMIN_EMAILS:-}`) and an empty value are both fine.

2. A file that mentions either variable carries no e-mail address and no
   public address. The reserved documentation ranges are fine - they can
   never be on a real list - and a real address is not.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

# The variables that carry the list.
LIST_VARIABLES = ("ADMIN_EMAILS", "ADMIN_IPS")

# An assignment of a value to one of them: `ADMIN_EMAILS=` followed by
# something. The value may be empty or a reference to the environment.
ASSIGNMENT = re.compile(
    r"^\s*(?:-\s*)?(?P<name>ADMIN_EMAILS|ADMIN_IPS)\s*[:=]\s*(?P<value>.*)$",
    re.MULTILINE,
)

# An e-mail address.
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

# An IPv4 address.
IPV4 = re.compile(r"(?<![\w.])((?:\d{1,3}\.){3}\d{1,3})(?![\w.])")

# Domains nobody can own (RFC 2606). An address at one of them is a
# placeholder, not a member of anyone's list.
RESERVED_DOMAINS = {
    "example",
    "example.com",
    "example.org",
    "example.net",
    "invalid",
    "localhost",
    "test",
}


def _repo_root() -> Path:
    # Navigate from apps/api/tests/unit/ to repo root.
    return Path(__file__).resolve().parents[4]


def _tracked_files() -> list[Path]:
    """Every file git tracks - i.e. everything a visitor can see on GitHub.

    Deliberately NOT a filesystem walk: the working tree also holds local-only,
    gitignored files (a personal .env, the operator's CLAUDE.md, editor
    settings). None of those are published, so none of them may fail here.
    """
    root = _repo_root()
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=root,
        capture_output=True,
        check=True,
    )
    names = [n for n in result.stdout.decode("utf-8").split("\0") if n]
    return [root / name for name in names]


def _relative(path: Path) -> Path:
    return path.relative_to(_repo_root())


def _is_reserved_domain(domain: str) -> bool:
    domain = domain.lower()
    return domain in RESERVED_DOMAINS or any(
        domain.endswith(f".{reserved}") for reserved in RESERVED_DOMAINS
    )


def _is_documentation_address(address: str) -> bool:
    """Is this address in a range that cannot be reached?

    RFC 5737 (the documentation ranges), RFC 1918 (the private ranges), the
    loopback and the link-local range. None of them can be a member of a real
    privileged list.
    """
    parts = address.split(".")
    if len(parts) != 4:
        return False
    try:
        octets = [int(part) for part in parts]
    except ValueError:
        return False
    if any(octet > 255 for octet in octets):
        return False

    first, second, third = octets[0], octets[1], octets[2]
    if first == 0 or first == 127:
        return True
    if first == 10:
        return True
    if first == 172 and 16 <= second <= 31:
        return True
    if first == 192 and second == 168:
        return True
    if first == 169 and second == 254:
        return True
    if first == 100 and 64 <= second <= 127:
        return True
    # The three documentation ranges of RFC 5737, each a /24.
    if (first, second, third) in ((192, 0, 2), (198, 51, 100), (203, 0, 113)):
        return True
    return False


def _text_files() -> list[Path]:
    files: list[Path] = []
    for path in _tracked_files():
        try:
            path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        files.append(path)
    return files


def test_no_file_assigns_a_value_to_the_privileged_list():
    offenders: list[str] = []
    for path in _text_files():
        text = path.read_text(encoding="utf-8")
        for match in ASSIGNMENT.finditer(text):
            value = match.group("value").strip()
            # An empty value and a reference to the environment are both fine.
            if not value or value.startswith("${"):
                continue
            offenders.append(f"{_relative(path)}: {match.group('name')}={value}")
    assert not offenders, "the privileged list is assigned in the tree:\n" + "\n".join(offenders)


def test_a_file_that_names_the_list_carries_no_address():
    offenders: list[str] = []
    for path in _text_files():
        text = path.read_text(encoding="utf-8")
        if not any(variable in text for variable in LIST_VARIABLES):
            continue
        for match in EMAIL.finditer(text):
            domain = match.group(0).rsplit("@", 1)[1]
            if _is_reserved_domain(domain):
                continue
            offenders.append(f"{_relative(path)}: {match.group(0)}")
        for match in IPV4.finditer(text):
            address = match.group(1)
            if _is_documentation_address(address):
                continue
            offenders.append(f"{_relative(path)}: {address}")
    assert not offenders, "a file that names the privileged list carries an address:\n" + "\n".join(
        offenders
    )


def test_the_list_is_read_from_the_environment_by_the_application():
    # The application reads the environment; it does not define the list.
    source = (_repo_root() / "apps" / "api" / "services" / "build_info.py").read_text(
        encoding="utf-8"
    )
    assert "os.getenv(ADMIN_EMAILS_ENV)" in source
    assert "os.getenv(ADMIN_IPS_ENV)" in source
    # The names live in constants, so a change of the environment's contract
    # is a change in one place.
    assert 'ADMIN_EMAILS_ENV = "ADMIN_EMAILS"' in source
    assert 'ADMIN_IPS_ENV = "ADMIN_IPS"' in source
