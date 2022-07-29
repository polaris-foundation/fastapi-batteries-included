import pytest
from pytest_httpx import HTTPXMock

from fastapi_batteries_included.helpers.security.jwk import (
    JwkCollection,
    retrieve_auth_provider_jwk,
)


class TestJwk:
    @pytest.fixture
    def dummy_jwks(self) -> JwkCollection:
        return {
            "keys": [
                {
                    "kid": "foo",
                    "kty": "oct",
                    "use": 123,
                    "n": 42,
                    "e": 65535,
                    "k": "hello",
                }
            ]
        }

    @pytest.fixture
    def mock_auth_provider(
        self,
        dummy_jwks: JwkCollection,
        httpx_mock: HTTPXMock,
    ) -> None:
        httpx_mock.add_response(
            url="https://login-sandbox.sensynehealth.com/.well-known/jwks.json",
            method="GET",
            json=dummy_jwks,
        )

    def test_fetch_auth_provider_jwks(self, mock_auth_provider: None) -> None:
        jwks = retrieve_auth_provider_jwk(key_id="foo")
        assert jwks == {
            "kid": "foo",
            "kty": "oct",
            "use": 123,
            "n": 42,
            "e": 65535,
            "k": "hello",
        }
