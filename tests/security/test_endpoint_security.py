import urllib
from typing import Any, Union
from urllib.parse import ParseResult

import pytest
from _pytest.monkeypatch import MonkeyPatch
from fastapi import Request
from pytest_mock import MockFixture

from fastapi_batteries_included.helpers.security import endpoint_security
from fastapi_batteries_included.helpers.security.endpoint_security import (
    ProtectedScopeEnvironment,
    and_,
    argument_not_present,
    argument_present,
    key_contains_value,
    key_contains_value_in_list,
    key_present,
    match_keys,
    non_production_only_route,
    or_,
    production_only_route,
    scopes_present,
)


def _create_request(url: str, json: object = None) -> Request:
    parsed: ParseResult = urllib.parse.urlparse(url, scheme="http")
    scope = {
        "type": "http",
        "scheme": parsed.scheme,
        "server": (parsed.hostname, parsed.port),
        "path": parsed.path,
        "query_string": parsed.query,
    }
    request = Request(scope)
    request._json = json
    return request


@pytest.mark.asyncio
class TestEndpointSecurity:
    @pytest.fixture
    def scopes(
        self,
    ) -> list[str]:
        return []

    @pytest.fixture
    def claims(
        self,
    ) -> dict[str, Any]:
        return {"patient_id": "12345"}

    @pytest.fixture
    def dummy_environment(
        self, mocker: MockFixture, scopes: list[str], claims: dict[str, Any]
    ) -> ProtectedScopeEnvironment:
        return ProtectedScopeEnvironment(
            scopes=scopes, claims=claims, request=_create_request("/endpoint")
        )

    async def test_valid_key_present(
        self, dummy_environment: ProtectedScopeEnvironment, claims: dict
    ) -> None:
        bound_function = key_present("patient_id")
        assert await bound_function(dummy_environment)

    async def test_invalid_key_present(
        self, dummy_environment: ProtectedScopeEnvironment, claims: dict
    ) -> None:
        bound_function = key_present("clinician")
        assert not await bound_function(dummy_environment)

    @pytest.mark.parametrize("claims", [{"patient_id": "12345"}])
    async def test_valid_or_(
        self, dummy_environment: ProtectedScopeEnvironment, claims: dict
    ) -> None:
        bound_function = or_(key_present("clinician_id"), key_present("patient_id"))
        assert await bound_function(dummy_environment)

    async def test_invalid_or_(
        self, dummy_environment: ProtectedScopeEnvironment
    ) -> None:
        bound_function = or_(key_present("clinician_id"), key_present("system_id"))
        assert not await bound_function(dummy_environment)

    async def test_valid_and_(
        self, dummy_environment: ProtectedScopeEnvironment
    ) -> None:
        bound_function = and_(key_present("patient_id"), key_present("patient_id"))
        assert await bound_function(dummy_environment)

    async def test_invalid_and_(
        self, dummy_environment: ProtectedScopeEnvironment
    ) -> None:
        jwt_claims = {"patient_id": "12345"}
        bound_function = and_(key_present("patient_id"), key_present("clinician_id"))
        assert not await bound_function(dummy_environment)

    async def test_valid_key_and_value(
        self, dummy_environment: ProtectedScopeEnvironment
    ) -> None:
        jwt_claims = {"patient_id": "12345"}
        bound_function = key_contains_value("patient_id", "12345")
        assert await bound_function(dummy_environment) is True

    async def test_invalid_key_and_valid_value(
        self, dummy_environment: ProtectedScopeEnvironment
    ) -> None:
        jwt_claims = {"patient_id": "12345"}
        bound_function = key_contains_value("clinician_id", "12345")
        assert await bound_function(dummy_environment) is False

    async def test_valid_key_and_invalid_value(
        self, dummy_environment: ProtectedScopeEnvironment
    ) -> None:
        jwt_claims = {"patient_id": "12345"}
        bound_function = key_contains_value("patient_id", "123456")
        assert await bound_function(dummy_environment) is False

    async def test_valid_key_and_list_of_values(
        self, dummy_environment: ProtectedScopeEnvironment
    ) -> None:
        jwt_claims = {"patient_id": "12345"}
        bound_function = key_contains_value_in_list("patient_id", ["12345", "67890"])
        assert await bound_function(dummy_environment) is True

    async def test_invalid_key_and_valid_list_of_values(
        self, dummy_environment: ProtectedScopeEnvironment
    ) -> None:
        jwt_claims = {"patient_id": "12345"}
        bound_function = key_contains_value_in_list("clinician_id", ["12345", "67890"])
        assert await bound_function(dummy_environment) is False

    async def test_valid_key_and_invalid_list_of_values(
        self, dummy_environment: ProtectedScopeEnvironment
    ) -> None:
        jwt_claims = {"patient_id": "12345"}
        bound_function = key_contains_value_in_list("patient_id", ["123456", "78901"])
        assert await bound_function(dummy_environment) is False

    @pytest.mark.parametrize(
        "scopes,required_scopes,is_valid",
        [
            (["read:user"], ["write:user"], False),
            (["read:user", "write:user"], ["write:users"], False),
            (
                ["read:user", "write:user", "read:patient"],
                ["read:user", "write:user", "read:patient", "write:patient"],
                False,
            ),
            (["read:user", "write:user"], "read:patient", False),
            (["read:user", "write:user"], ["write:user"], True),
            (["read:user", "write:user"], ["read:user", "write:user"], True),
            (
                ["read:user", "write:user", "read:patient"],
                ["write:user", "read:patient"],
                True,
            ),
            (["read:user", "write:user", "read:patient"], "read:user", True),
        ],
    )
    async def test_scopes(
        self,
        dummy_environment: ProtectedScopeEnvironment,
        scopes: list[str],
        required_scopes: Union[str, list[str]],
        is_valid: bool,
    ) -> None:
        bound_function = scopes_present(required_scopes=required_scopes)
        assert await bound_function(dummy_environment) is is_valid

    async def test_compare_keys_no_expected_params(
        self, dummy_environment: ProtectedScopeEnvironment
    ) -> None:
        comparator = match_keys()
        assert await comparator(dummy_environment) is True

    async def test_compare_keys_expected_params_not_supplied(
        self, dummy_environment: ProtectedScopeEnvironment
    ) -> None:
        comparator = match_keys(patient_id="patient_id")
        assert await comparator(dummy_environment) is False

    async def test_compare_keys_with_expected_params(
        self, dummy_environment: ProtectedScopeEnvironment
    ) -> None:
        comparator = match_keys(patient_id="patient_id")
        dummy_environment.request.scope["path_params"] = {"patient_id": "12345"}
        assert await comparator(dummy_environment) is True

    async def test_compare_keys_without_expected_params(
        self, dummy_environment: ProtectedScopeEnvironment
    ) -> None:
        dummy_environment.claims = {"patient_id": "WRONG_ID_IN_JWT"}
        dummy_environment.request.scope["path_params"] = {"patient_id": "12345"}
        comparator = match_keys(patient_id="patient_id")

        assert await comparator(dummy_environment) is False

    async def test_compare_keys_with_expected_params_not_in_route_param_list(
        self, dummy_environment: ProtectedScopeEnvironment
    ) -> None:
        dummy_environment.claims = {"claim_field_1": ["claim_1_value"]}
        dummy_environment.request.scope["path_params"] = {
            "route_param_1": "claim_2_value"
        }
        comparator = match_keys(route_param_1="claim_field_1")

        assert await comparator(dummy_environment) is False

    async def test_compare_keys_param_dict(
        self, dummy_environment: ProtectedScopeEnvironment
    ) -> None:
        dummy_environment.claims = {"claim_field_1": {"claim_1_value": None}}
        dummy_environment.request.scope["path_params"] = {
            "route_param_1": "claim_2_value"
        }
        comparator = match_keys(route_param_1="claim_field_1")

        assert await comparator(dummy_environment) is False

    async def test_argument_present(
        self,
    ) -> None:
        f = argument_present(argument="arg1", expected_value="val1")

        request = _create_request(
            "/dhos/v1/patient?arg1=val1", json={"format": "short"}
        )
        assert await f(ProtectedScopeEnvironment(request=request)) is True

    async def test_argument_present_of_multiple(
        self,
    ) -> None:
        f = argument_present(argument="arg1", expected_value="val1")
        request = _create_request(
            "/dhos/v1/patient?arg1=val1&arg2=val2", json={"format": "short"}
        )
        assert await f(ProtectedScopeEnvironment(request=request)) is True

    async def test_argument_present_fails(
        self,
    ) -> None:
        f = argument_present(argument="arg1", expected_value="val1")
        request = _create_request(
            "/dhos/v1/patient?arg1=val2", json={"format": "short"}
        )
        assert await f(ProtectedScopeEnvironment(request=request)) is False

    async def test_not_argument_present(
        self,
    ) -> None:
        f = argument_not_present(argument="arg1")
        request = _create_request(
            "/dhos/v1/patient?arg2=val1", json={"format": "short"}
        )
        assert await f(ProtectedScopeEnvironment(request=request)) is True

    async def test_not_argument_present_fails(self) -> None:
        f = argument_not_present(argument="arg2")
        request = _create_request(
            "/dhos/v1/patient?arg2=val1", json={"format": "short"}
        )
        assert await f(ProtectedScopeEnvironment(request=request)) is False

    async def test_production_only_route_prod(
        self,
        monkeypatch: MonkeyPatch,
        dummy_environment: ProtectedScopeEnvironment,
    ) -> None:
        monkeypatch.setenv("ENVIRONMENT", "PRODUCTION")
        f = production_only_route()
        assert await f(dummy_environment) is True

    async def test_production_only_route_dev(
        self, monkeypatch: MonkeyPatch, dummy_environment: ProtectedScopeEnvironment
    ) -> None:
        monkeypatch.setenv("ENVIRONMENT", "DEVELOPMENT")
        f = production_only_route()
        assert await f(dummy_environment) is False

    async def test_non_production_only_route_prod(
        self, monkeypatch: MonkeyPatch, dummy_environment: ProtectedScopeEnvironment
    ) -> None:
        monkeypatch.setenv("ENVIRONMENT", "PRODUCTION")
        f = non_production_only_route()
        assert await f(dummy_environment) is False

    async def test_non_production_only_route_dev(
        self, monkeypatch: MonkeyPatch, dummy_environment: ProtectedScopeEnvironment
    ) -> None:
        monkeypatch.setenv("ENVIRONMENT", "DEVELOPMENT")
        f = non_production_only_route()
        assert await f(dummy_environment) is True

    @pytest.mark.parametrize(
        ["jwt_claim", "request_path_field", "expected"],
        [
            ("12345", "12345", True),
            ("abcde", "12345", False),
            ("12345", None, False),
            (None, "12345", False),
            (None, None, False),
        ],
    )
    async def test_field_in_path_matches_jwt_claim(
        self,
        dummy_environment: ProtectedScopeEnvironment,
        jwt_claim: str,
        request_path_field: str,
        expected: bool,
    ) -> None:
        dummy_environment.claims = {"patient_id": jwt_claim}
        dummy_environment.request.scope["path_params"] = {
            "patient_uuid": request_path_field
        }
        f = endpoint_security.field_in_path_matches_jwt_claim(
            path_field_name="patient_uuid", jwt_claim_name="patient_id"
        )
        assert await f(dummy_environment) is expected

    @pytest.mark.parametrize(
        ["jwt_claim", "request_body_field", "expected"],
        [
            ("12345", "12345", True),
            ("abcde", "12345", False),
            ("12345", None, False),
            (None, "12345", False),
            (None, None, False),
        ],
    )
    async def test_field_in_body_matches_jwt_claim(
        self,
        dummy_environment: ProtectedScopeEnvironment,
        jwt_claim: str,
        request_body_field: str,
        expected: bool,
    ) -> None:
        dummy_environment.claims = {"patient_id": jwt_claim}
        dummy_environment.request._json = {"patient_uuid": request_body_field}

        f = endpoint_security.field_in_body_matches_jwt_claim(
            body_field_name="patient_uuid", jwt_claim_name="patient_id"
        )
        assert await f(dummy_environment) is expected
