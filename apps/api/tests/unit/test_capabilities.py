"""The capabilities describe what the deployment can actually do.

A capability that promises a browser flow the deployment cannot deliver is
worse than a missing one: the visitor clicks the button and lands on a JSON
body. The OAuth callback sends the visitor back to the interface only when
the frontend URL is one it can redirect to, so the capability that the
interface reads has to ask the same question.
"""

from unittest.mock import MagicMock, patch

from api.routers.capabilities import build_capabilities


def _settings(**overrides):
    """A deployment with Google and Apple configured."""
    settings = MagicMock()
    settings.auth_jwt_enabled = True
    settings.auth_oauth_google_enabled = True
    settings.google_client_id = "client-id"
    settings.google_client_secret = (
        "client-secret"  # pragma: allowlist secret - a fake value in a test
    )
    settings.google_redirect_uri = "https://api.example.com/api/v1/auth/oauth/callback"
    settings.auth_oauth_apple_enabled = True
    settings.apple_client_id = "apple-client-id"
    settings.apple_team_id = "apple-team-id"
    settings.apple_private_key_path = "/run/secrets/apple.p8"
    settings.frontend_url = "https://app.example.com"
    settings.demo_user_bypass = False
    settings.demo_mode = False
    settings.demo_llm_mode = False
    settings.default_provider = "minimax"
    settings.default_model = "MiniMax-M3.1-Flash"
    settings.sentry_dsn = None
    for name, value in overrides.items():
        setattr(settings, name, value)
    return settings


def _capabilities(**overrides):
    """The capabilities of a deployment."""
    with patch("api.routers.capabilities.get_settings") as mock_settings:
        mock_settings.return_value = _settings(**overrides)
        return build_capabilities(email_enabled=False)


class TestTheOAuthCapabilities:
    """The flag the interface reads is the flag the endpoint can deliver."""

    def test_a_configured_google_is_advertised(self):
        capabilities = _capabilities()

        assert capabilities["auth"]["oauth"]["google"] is True
        assert capabilities["auth"]["oauth"]["apple"] is True

    def test_a_deployment_without_a_frontend_url_does_not_advertise_the_browser_flow(self):
        # Without one the callback answers with the tokens as a JSON body -
        # the session is set, but the visitor is left looking at JSON.
        capabilities = _capabilities(frontend_url=None)

        assert capabilities["auth"]["oauth"]["google"] is False
        assert capabilities["auth"]["oauth"]["apple"] is False

    def test_a_frontend_url_that_is_not_a_url_does_not_advertise_the_browser_flow(self):
        capabilities = _capabilities(frontend_url="app.example.com")

        assert capabilities["auth"]["oauth"]["google"] is False

    def test_a_deployment_without_the_credentials_does_not_advertise_google(self):
        capabilities = _capabilities(google_client_id=None)

        assert capabilities["auth"]["oauth"]["google"] is False

    def test_a_deployment_without_the_redirect_uri_does_not_advertise_google(self):
        capabilities = _capabilities(google_redirect_uri=None)

        assert capabilities["auth"]["oauth"]["google"] is False

    def test_a_deployment_without_jwt_does_not_advertise_google(self):
        # Without JWT the whole auth router does not exist - the click would
        # answer 404.
        capabilities = _capabilities(auth_jwt_enabled=False)

        assert capabilities["auth"]["oauth"]["google"] is False
