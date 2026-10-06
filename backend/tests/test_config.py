"""Settings-level guards for insecure or self-defeating configuration."""

import warnings

import pytest
from pydantic import ValidationError

from app.core.config import _DEFAULT_JWT_SECRET, Settings

_STRONG_SECRET = "a" * 48


def _warnings_for(**overrides) -> list[str]:
    # Pin the environment so an ambient ENVIRONMENT=production in CI cannot
    # turn these warning assertions into hard validation failures.
    params = {"environment": "development", **overrides}
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        Settings(**params)
    return [str(w.message) for w in caught]


def test_secure_cookie_over_http_warns():
    messages = _warnings_for(
        cookie_secure=True, app_base_url="http://<your-host-ip>:3010"
    )
    assert any("COOKIE_SECURE=true" in m for m in messages)


def test_secure_cookie_over_https_does_not_warn():
    messages = _warnings_for(cookie_secure=True, app_base_url="https://pay.example.com")
    assert not any("COOKIE_SECURE=true" in m for m in messages)


def test_secure_cookie_on_localhost_does_not_warn():
    messages = _warnings_for(cookie_secure=True, app_base_url="http://localhost:3010")
    assert not any("COOKIE_SECURE=true" in m for m in messages)


def test_insecure_cookie_over_http_does_not_warn():
    messages = _warnings_for(
        cookie_secure=False, app_base_url="http://<your-host-ip>:3010"
    )
    assert not any("COOKIE_SECURE=true" in m for m in messages)


def test_plain_cookie_over_https_warns():
    messages = _warnings_for(
        cookie_secure=False, app_base_url="https://pay.example.com"
    )
    assert any("COOKIE_SECURE=false" in m for m in messages)


def test_plain_cookie_over_http_does_not_warn_https_mismatch():
    messages = _warnings_for(cookie_secure=False, app_base_url="http://pay.example.com")
    assert not any("COOKIE_SECURE=false" in m for m in messages)


# ---------------------------------------------------------------------------
# JWT secret / algorithm
# ---------------------------------------------------------------------------


def test_jwt_secret_is_secret_str():
    s = Settings(jwt_secret="super-secret-value-that-is-long-enough")
    assert s.jwt_secret.get_secret_value() == "super-secret-value-that-is-long-enough"
    assert "super-secret-value-that-is-long-enough" not in repr(s)


def test_production_rejects_default_jwt_secret():
    with pytest.raises(ValidationError, match="default placeholder"):
        Settings(environment="production", jwt_secret=_DEFAULT_JWT_SECRET)


def test_production_rejects_short_jwt_secret():
    with pytest.raises(ValidationError, match="at least 32"):
        Settings(environment="production", jwt_secret="too-short")


def test_production_accepts_strong_jwt_secret():
    s = Settings(environment="production", jwt_secret=_STRONG_SECRET)
    assert s.is_production is True


def test_non_production_warns_but_allows_short_jwt_secret():
    messages = _warnings_for(jwt_secret="too-short", environment="development")
    assert any("JWT_SECRET is weak" in m for m in messages)


def test_jwt_algorithm_allowlist():
    for algorithm in ("HS256", "HS384", "HS512"):
        assert Settings(jwt_algorithm=algorithm).jwt_algorithm == algorithm
    for algorithm in ("none", "RS256", "ES256", ""):
        with pytest.raises(ValidationError, match="JWT_ALGORITHM"):
            Settings(jwt_algorithm=algorithm)


def test_apprise_base_url_trailing_slashes_are_stripped():
    s = Settings(apprise_base_url="http://apprise:8000///")
    assert s.apprise_base_url == "http://apprise:8000"


def test_apprise_configured_needs_only_a_base_url():
    assert Settings(apprise_base_url=None).apprise_configured is False
    assert Settings(apprise_base_url="http://x").apprise_configured is True
    assert (
        Settings(
            apprise_base_url="http://x", apprise_urls="ntfy://topic"
        ).apprise_configured
        is True
    )
    assert (
        Settings(
            apprise_base_url="http://x", apprise_key="household"
        ).apprise_configured
        is True
    )
