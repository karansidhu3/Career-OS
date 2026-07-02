from unittest.mock import MagicMock, patch

from app.services import error_tracking


def test_init_is_noop_without_dsn():
    with patch.object(error_tracking.settings, "sentry_dsn", ""):
        with patch("sentry_sdk.init") as mock_init:
            error_tracking.init_error_tracking()
            mock_init.assert_not_called()


def test_init_calls_sentry_sdk_when_dsn_set():
    with patch.object(error_tracking.settings, "sentry_dsn", "https://example@sentry.io/1"):
        with patch("sentry_sdk.init") as mock_init:
            error_tracking.init_error_tracking()
            mock_init.assert_called_once()
            _, kwargs = mock_init.call_args
            assert kwargs["dsn"] == "https://example@sentry.io/1"
            assert kwargs["send_default_pii"] is False


def test_set_user_context_is_noop_without_dsn():
    with patch.object(error_tracking.settings, "sentry_dsn", ""):
        with patch("sentry_sdk.set_user") as mock_set_user:
            error_tracking.set_user_context("user-123")
            mock_set_user.assert_not_called()


def test_set_user_context_sets_only_id_when_dsn_set():
    with patch.object(error_tracking.settings, "sentry_dsn", "https://example@sentry.io/1"):
        with patch("sentry_sdk.set_user") as mock_set_user:
            error_tracking.set_user_context("user-123")
            mock_set_user.assert_called_once_with({"id": "user-123"})


def test_scrub_pii_removes_authorization_and_cookie_headers():
    event = {"request": {"headers": {"Authorization": "Bearer secret", "Cookie": "session=abc", "Content-Type": "application/json"}}}
    scrubbed = error_tracking._scrub_pii(event, {})
    headers = scrubbed["request"]["headers"]
    assert "Authorization" not in headers
    assert "Cookie" not in headers
    assert headers["Content-Type"] == "application/json"


def test_scrub_pii_handles_missing_request_or_headers():
    assert error_tracking._scrub_pii({}, {}) == {}
    assert error_tracking._scrub_pii({"request": {}}, {}) == {"request": {}}
