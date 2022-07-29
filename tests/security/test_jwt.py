import pytest
from _pytest.monkeypatch import MonkeyPatch
from jose import jwt as jose_jwt
from pytest_httpx import HTTPXMock
from pytest_mock import MockFixture

from fastapi_batteries_included.helpers.security import jwt_parsers
from fastapi_batteries_included.helpers.security.jwt import (
    TokenData,
    current_jwt_user,
    decode_hs_jwt,
    jwt_settings,
)
from fastapi_batteries_included.helpers.security.jwt_parsers import JwtParser

SAMPLE_JWT_EXPIRED = (
    r"eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJtZXRhZGF0YSI6eyJzeXN0ZW1faWQiO"
    r"iJkaG9zLXJvYm90In0sImlzcyI6Imh0dHA6Ly9lcHIvIiwiYXVkIjoiaHR0cDovL2xvY2F"
    r"saG9zdC8iLCJzY29wZSI6IlNPTUVUSElORyIsImV4cCI6MTU0NDU0OTE5MH0.JhtT_lhOM"
    "M86otB2uNMX4bP4VFuxu-r0pyzSSIc4RS5N6gb-l4vaXLgIMXHxJ7q49jLG8KxLng4Vdr8F"
    "BmhVlA "
)


@pytest.fixture
def mock_old_user_id_keys(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(
        jwt_settings,
        "VALID_USER_ID_KEYS",
        {"clinician_id", "device_id", "patient_id", "system_id"},
    )


@pytest.mark.parametrize(
    "user_id_key", ["clinician_id", "device_id", "patient_id", "system_id"]
)
def test_current_jwt_user_clinician(
    user_id_key: str, mock_old_user_id_keys: None
) -> None:
    token = TokenData(claims={user_id_key: "12345"})
    assert current_jwt_user(token) == "12345"


def test_current_jwt_user_invalid(mock_old_user_id_keys: None) -> None:
    token = TokenData(claims={"something_id": "12345"})
    assert current_jwt_user(token) == "unknown"


def test_decode_hs_jwt_expired() -> None:
    options: dict = JwtParser._construct_verification_options(True)
    decoded = decode_hs_jwt(
        hs_key="secret2",
        jwt_token=SAMPLE_JWT_EXPIRED,
        algorithms=["HS512"],
        decode_options=options,
    )

    assert decoded is None


TEST_JWKS = {
    "keys": [
        {"kid": "foo", "kty": "oct", "use": 123, "n": 42, "e": 65535, "k": "hello"}
    ]
}


def test_jwt_parser(
    httpx_mock: HTTPXMock,
    mocker: MockFixture,
) -> None:
    audience = "http://localhost/"
    metadata_key: str = "metadata"
    issuer_to_verify: str = "http://epr/"

    httpx_mock.add_response(
        url="https://login-sandbox.sensynehealth.com/.well-known/jwks.json",
        method="GET",
        json=TEST_JWKS,
    )

    jwt_parser: JwtParser = jwt_parsers.AuthProviderJwtParser(
        required_audience=audience,
        required_issuer=issuer_to_verify,
        allowed_algorithms=["HS512"],
        metadata_key=metadata_key,
        verify=True,
    )

    mocker.patch.object(
        jose_jwt,
        "decode",
        return_value={"metadata": {"system_id": "pytest id"}, "scope": "SOMETHING"},
    )

    token_data = jwt_parser.decode_jwt(
        jwt_token=r"a.b.c", unverified_header={"kid": "foo"}
    )

    assert "system_id" in token_data.claims
    assert token_data.scopes == ["SOMETHING"]
