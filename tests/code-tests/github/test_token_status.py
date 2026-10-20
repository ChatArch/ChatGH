from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

import pytest
import requests

from chatgh.github.token_status import check_token


NOW = datetime(2026, 10, 20, 12, tzinfo=timezone.utc)
TOKEN = "synthetic-token-must-never-appear-in-results"


def response(status=200, expiration=None):
    result = Mock(status_code=status)
    result.headers = requests.structures.CaseInsensitiveDict()
    if expiration is not None:
        result.headers["GitHub-Authentication-Token-Expiration"] = expiration
    return result


@pytest.mark.parametrize(
    "header",
    ["2026-10-30 12:00:00 UTC", "2026-10-30 08:00:00 -0400", "2026-10-30T12:00:00Z"],
)
def test_expiration_formats_and_scoped_authenticated_request(header):
    with patch("requests.get", return_value=response(expiration=header)) as get:
        result = check_token(TOKEN, now=NOW)
    assert result["status"] == "valid"
    assert result["valid"] is True
    assert result["expires_at"] == "2026-10-30T12:00:00Z"
    assert result["days_remaining"] == 10
    args, kwargs = get.call_args
    assert args == ("https://api.github.com/user",)
    assert kwargs["headers"]["Authorization"] == f"Bearer {TOKEN}"
    assert kwargs["allow_redirects"] is False
    assert kwargs["timeout"] == (5, 15)
    assert TOKEN not in str(result)


@pytest.mark.parametrize("days,status", [(7, "expiring"), (0.5, "expiring"), (0, "expired"), (-1, "expired")])
def test_warning_boundary_and_expiration(days, status):
    header = (NOW + timedelta(days=days)).isoformat()
    with patch("requests.get", return_value=response(expiration=header)):
        result = check_token(TOKEN, now=NOW)
    assert result["status"] == status
    assert result["days_remaining"] == days
    assert result["valid"] is (days > 0)


@pytest.mark.parametrize("header", [None, "unparseable", "2026-10-30 12:00:00"])
def test_absent_malformed_or_timezone_less_expiration_is_unknown(header):
    with patch("requests.get", return_value=response(expiration=header)):
        result = check_token(TOKEN, now=NOW)
    assert result["valid"] is True
    assert result["expires_at"] is None
    assert result["days_remaining"] is None
    assert "unknown" in result["message"].lower()


def test_bad_credentials_do_not_claim_definite_expiration():
    with patch("requests.get", return_value=response(401)):
        result = check_token(TOKEN, now=NOW)
    assert result["status"] == "invalid"
    assert result["valid"] is False
    assert result["http_status"] == 401
    assert result["expires_at"] is None
    assert "revoked" in result["message"]


@pytest.mark.parametrize("status", [302, 403, 404, 429, 500, 503])
def test_other_http_failures_leave_validity_unknown(status):
    with patch("requests.get", return_value=response(status)):
        result = check_token(TOKEN, now=NOW)
    assert result["status"] == "error"
    assert result["valid"] is None
    assert result["http_status"] == status


@pytest.mark.parametrize("exception", [requests.Timeout(TOKEN), requests.ConnectionError(TOKEN), requests.exceptions.InvalidHeader(TOKEN)])
def test_request_failures_do_not_leak_exception_or_token(exception):
    with patch("requests.get", side_effect=exception):
        result = check_token(TOKEN, now=NOW)
    assert result["status"] == "error"
    assert result["valid"] is None
    assert TOKEN not in str(result)


@pytest.mark.parametrize("token", [None, "", "  "])
def test_missing_token_never_sends_anonymous_request(token):
    with patch("requests.get") as get:
        result = check_token(token, now=NOW)
    get.assert_not_called()
    assert result["status"] == "missing"
    assert result["valid"] is False


def test_custom_warning_threshold():
    with patch("requests.get", return_value=response(expiration="2026-10-30 12:00:00 UTC")):
        assert check_token(TOKEN, now=NOW, warning_days=14)["status"] == "expiring"


@pytest.mark.parametrize("token", ["synthetic-token\n", "synthetic-token\t", "synthetic-token-非ASCII"])
def test_invalid_header_characters_fail_without_exposing_credentials(token):
    with patch("requests.get") as get:
        result = check_token(token, now=NOW)
    get.assert_not_called()
    assert result["status"] == "invalid"
    assert token not in str(result)


def test_netrc_cannot_replace_selected_pat_and_proxy_support_remains(monkeypatch):
    monkeypatch.setenv("HTTPS_PROXY", "http://synthetic-proxy.invalid:8080")
    received = requests.Response()
    received.status_code = 200
    received._content = b"{}"
    received.headers["GitHub-Authentication-Token-Expiration"] = "2026-10-30 12:00:00 UTC"
    with patch("requests.sessions.get_netrc_auth", return_value=("other-user", "other-token")) as netrc:
        with patch("requests.Session.send", return_value=received) as send:
            result = check_token(TOKEN, now=NOW)
    netrc.assert_not_called()
    request = send.call_args.args[0]
    assert request.headers["Authorization"] == f"Bearer {TOKEN}"
    assert send.call_args.kwargs["proxies"]["https"] == "http://synthetic-proxy.invalid:8080"
    assert result["valid"] is True
