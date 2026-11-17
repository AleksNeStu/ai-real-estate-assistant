from __future__ import annotations

import os
import sys  # noqa: E402
from pathlib import Path
from unittest.mock import patch

import pytest  # noqa: E402

# Add project root to Python path for scripts imports
# (top-level, before any test imports)
# From apps/api/tests/unit/ to project root: 4 levels up
_project_root = Path(__file__).resolve().parents[4]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from scripts.docker.compose_smoke import (  # noqa: E402
    SmokeConfig,
    build_compose_base_command,
    build_compose_down_command,
    build_compose_up_command,
    get_default_api_access_key_from_env,
    http_get_status,
    main,
    parse_args,
    wait_for_http_ok,
)


def test_build_compose_commands(tmp_path):
    compose_file = tmp_path / "docker-compose.yml"
    compose_file.write_text("version: '3.8'\nservices: {}\n", encoding="utf-8")

    base = build_compose_base_command(compose_file)
    assert base[:3] == ["docker", "compose", "-f"]
    assert base[3] == str(compose_file)

    up_no_build = build_compose_up_command(base, build=False)
    assert "--build" not in up_no_build

    up_build = build_compose_up_command(base, build=True)
    assert "--build" in up_build

    down = build_compose_down_command(base)
    assert down[-3:] == ["down", "--volumes", "--remove-orphans"]


def test_wait_for_http_ok_succeeds_after_retries():
    statuses = [503, 503, 200]

    def _get_status(_url: str, _timeout: float) -> int:
        result = statuses.pop(0)
        assert isinstance(result, int)
        return result

    sleeps: list[float] = []

    def _sleep(seconds: float) -> None:
        sleeps.append(seconds)

    wait_for_http_ok(
        "http://example/health",
        timeout_seconds=5,
        interval_seconds=0.1,
        get_status=_get_status,
        sleep=_sleep,
    )

    assert sleeps


def test_wait_for_http_ok_times_out_immediately():
    def _get_status(_url: str, _timeout: float) -> int:
        return 500

    with pytest.raises(TimeoutError):
        wait_for_http_ok(
            "http://example/health",
            timeout_seconds=0,
            interval_seconds=0.0,
            get_status=_get_status,
            sleep=lambda _: None,
        )


def test_parse_args_ci_overrides_defaults(tmp_path):
    compose_file = tmp_path / "docker-compose.yml"
    compose_file.write_text("version: '3.8'\nservices: {}\n", encoding="utf-8")

    cfg = parse_args(
        [
            "--compose-file",
            str(compose_file),
            "--timeout-seconds",
            "10",
            "--ci",
        ]
    )

    assert isinstance(cfg, SmokeConfig)
    assert cfg.build is True
    assert cfg.down is True
    assert cfg.timeout_seconds >= 240


def test_get_default_api_access_key_from_env_prefers_primary_key():
    with patch.dict(
        os.environ,
        {"API_ACCESS_KEY": " primary ", "API_ACCESS_KEYS": "rot1,rot2"},
        clear=False,  # noqa: E501
    ):
        assert get_default_api_access_key_from_env() == "primary"


def test_get_default_api_access_key_from_env_falls_back_to_rotated_keys():
    with patch.dict(
        os.environ,
        {"API_ACCESS_KEY": "   ", "API_ACCESS_KEYS": " rot1 , rot2 "},
        clear=False,  # noqa: E501
    ):
        assert get_default_api_access_key_from_env() == "rot1"


def test_main_dry_run_prints_commands(tmp_path, capsys):
    compose_file = tmp_path / "docker-compose.yml"
    compose_file.write_text("version: '3.8'\nservices: {}\n", encoding="utf-8")

    rc = main(["--compose-file", str(compose_file), "--dry-run"])
    assert rc == 0

    out = capsys.readouterr().out
    assert "UP:" in out
    assert "DOWN:" in out
    assert "CHECK:" in out
    assert "CHECK_AUTH:" in out


def test_main_missing_compose_file_raises(tmp_path):
    missing_path = str(tmp_path / "missing-compose.yml")  # noqa: E501
    with pytest.raises(FileNotFoundError):
        main(["--compose-file", missing_path, "--dry-run"])


def test_main_ci_runs_up_waits_and_tears_down(tmp_path):
    compose_file = tmp_path / "docker-compose.yml"
    compose_file.write_text("version: '3.8'\nservices: {}\n", encoding="utf-8")

    with (
        patch.dict(os.environ, {"API_ACCESS_KEY": "ci-test-key"}, clear=False),
        patch("scripts.docker.compose_smoke.run_command") as run_command_mock,
        patch("scripts.docker.compose_smoke.wait_for_http_ok") as wait_mock,
    ):
        rc = main(["--compose-file", str(compose_file), "--ci"])

    assert rc == 0
    assert wait_mock.call_count == 3
    assert run_command_mock.call_count == 2

    up_cmd = run_command_mock.call_args_list[0].args[0]
    down_cmd = run_command_mock.call_args_list[1].args[0]
    assert "up" in up_cmd
    assert "down" in down_cmd


def test_main_ci_skips_verify_auth_when_api_key_missing(tmp_path):
    compose_file = tmp_path / "docker-compose.yml"
    compose_file.write_text("version: '3.8'\nservices: {}\n", encoding="utf-8")

    with (
        patch.dict(
            os.environ,
            {"API_ACCESS_KEY": "", "API_ACCESS_KEYS": ""},
            clear=False,  # noqa: E501
        ),
        patch("scripts.docker.compose_smoke.run_command") as run_command_mock,
        patch("scripts.docker.compose_smoke.wait_for_http_ok") as wait_mock,
    ):
        rc = main(["--compose-file", str(compose_file), "--ci"])

    assert rc == 0
    assert wait_mock.call_count == 2
    assert run_command_mock.call_count == 2


def test_main_ci_uses_api_access_keys_when_primary_key_missing(tmp_path):
    compose_file = tmp_path / "docker-compose.yml"
    compose_file.write_text("version: '3.8'\nservices: {}\n", encoding="utf-8")

    with (
        patch.dict(
            os.environ,
            {"API_ACCESS_KEY": "", "API_ACCESS_KEYS": "k1,k2"},
            clear=False,  # noqa: E501
        ),
        patch("scripts.docker.compose_smoke.run_command") as run_command_mock,
        patch("scripts.docker.compose_smoke.wait_for_http_ok") as wait_mock,
    ):
        rc = main(["--compose-file", str(compose_file), "--ci"])

    assert rc == 0
    assert wait_mock.call_count == 3
    assert run_command_mock.call_count == 2


def test_main_ci_tears_down_on_wait_timeout(tmp_path):
    compose_file = tmp_path / "docker-compose.yml"
    compose_file.write_text("version: '3.8'\nservices: {}\n", encoding="utf-8")

    with (
        patch("scripts.docker.compose_smoke.run_command") as run_command_mock,
        patch(
            "scripts.docker.compose_smoke.wait_for_http_ok",  # noqa: E501
            side_effect=TimeoutError("boom"),
        ),
    ):
        with pytest.raises(TimeoutError):
            main(["--compose-file", str(compose_file), "--ci"])

    assert run_command_mock.call_count >= 2
    assert "up" in run_command_mock.call_args_list[0].args[0]  # noqa: E501
    assert "down" in run_command_mock.call_args_list[-1].args[0]  # noqa: E501
    assert any("ps" in call.args[0] for call in run_command_mock.call_args_list)  # noqa: E501
    assert any(  # noqa: E501
        "logs" in call.args[0] for call in run_command_mock.call_args_list
    )


def test_http_get_status_returns_http_error_code():
    import urllib.error

    err = urllib.error.HTTPError(
        url="http://example",
        code=418,
        msg="teapot",
        hdrs=None,
        fp=None,
    )
    with patch("urllib.request.urlopen", side_effect=err):
        assert http_get_status("http://example", timeout_seconds=0.1) == 418


def test_http_get_status_sends_headers():
    class _Resp:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def _fake_urlopen(req, timeout: float | None = None) -> _Resp:
        del timeout
        assert req.headers.get("X-api-key") == "k"
        return _Resp()

    with patch("urllib.request.urlopen", side_effect=_fake_urlopen):
        assert (  # noqa: E501
            http_get_status(
                "http://example",
                timeout_seconds=0.1,
                headers={"X-API-Key": "k"},
            )
            == 200
        )


def test_parse_args_defaults_probe_the_published_compose_ports(tmp_path):
    """The smoke test has to probe the ports the compose file publishes.

    The old defaults (8001/3001) are the ports of the local non-Docker
    stack. The compose file publishes 8082 and 3082, so the smoke test was
    waiting out its whole timeout for a host the stack never opens - in CI,
    where nothing else listens, that is the difference between a green and a
    red job.
    """
    compose_file = tmp_path / "docker-compose.yml"
    compose_file.write_text("version: '3.8'\nservices: {}\n", encoding="utf-8")

    cfg = parse_args(["--compose-file", str(compose_file)])

    assert cfg.backend_health_url == "http://localhost:8082/health"
    assert cfg.backend_verify_auth_url == "http://localhost:8082/api/v1/verify-auth"
    assert cfg.frontend_url == "http://localhost:3082/"


def test_parse_args_keep_up_leaves_the_stack_running(tmp_path):
    """--keep-up keeps the stack up so the caller can run against it.

    The CI job starts the stack, runs the e2e suite against it and tears it
    down itself; the smoke script must not pull the stack down at the end of
    the health checks.
    """
    compose_file = tmp_path / "docker-compose.yml"
    compose_file.write_text("version: '3.8'\nservices: {}\n", encoding="utf-8")

    cfg = parse_args(["--compose-file", str(compose_file), "--ci", "--keep-up"])

    assert cfg.build is True
    assert cfg.down is False
