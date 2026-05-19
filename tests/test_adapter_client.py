"""Unit tests for adapters/client.py — no network calls."""

from unittest.mock import MagicMock, patch

import pytest


class TestMakeClient:
    def test_returns_httpx_client(self):
        import httpx
        from chatgh.adapters.client import make_client

        client = make_client(token="test-token")
        assert isinstance(client, httpx.Client)

    def test_token_in_headers(self):
        from chatgh.adapters.client import make_client

        client = make_client(token="mytoken")
        assert client.headers.get("authorization") == "Bearer mytoken"

    def test_no_auth_header_without_token(self):
        """No token → no Authorization header."""
        with patch("chatgh.adapters.client._token_from_git_credentials", return_value=None), \
             patch.dict("os.environ", {}, clear=True):
            from chatgh.adapters.client import make_client
            client = make_client()
            assert "authorization" not in dict(client.headers)

    def test_explicit_token_takes_priority(self):
        """Explicit token beats git credentials."""
        with patch("chatgh.adapters.client._token_from_git_credentials", return_value="git-token"):
            from chatgh.adapters.client import make_client
            client = make_client(token="explicit-token")
            assert "explicit-token" in client.headers.get("authorization", "")

    def test_base_url(self):
        from chatgh.adapters.client import make_client, GITHUB_API_BASE

        client = make_client(token="tok")
        assert str(client.base_url).rstrip("/") == GITHUB_API_BASE.rstrip("/")

    def test_env_token_fallback(self):
        with patch("chatgh.adapters.client._token_from_git_credentials", return_value=None), \
             patch.dict("os.environ", {"GITHUB_TOKEN": "env-token"}):
            from chatgh.adapters.client import make_client
            client = make_client()
            assert "env-token" in client.headers.get("authorization", "")


class TestTokenFromGitCredentials:
    def test_returns_none_on_error(self):
        from chatgh.adapters.client import _token_from_git_credentials
        with patch("subprocess.run", side_effect=OSError):
            assert _token_from_git_credentials() is None

    def test_returns_none_on_nonzero_exit(self):
        from chatgh.adapters.client import _token_from_git_credentials
        mock = MagicMock(returncode=1, stdout="")
        with patch("subprocess.run", return_value=mock):
            assert _token_from_git_credentials() is None

    def test_parses_password_line(self):
        from chatgh.adapters.client import _token_from_git_credentials
        mock = MagicMock(returncode=0, stdout="protocol=https\nhost=github.com\npassword=abc123\n")
        with patch("subprocess.run", return_value=mock):
            assert _token_from_git_credentials() == "abc123"
