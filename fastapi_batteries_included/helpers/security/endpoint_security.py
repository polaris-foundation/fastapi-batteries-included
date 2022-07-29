from typing import Any, Optional, Protocol, Union

import fastapi
from pydantic import BaseModel
from she_logging import logger

from fastapi_batteries_included.config import (
    is_not_production_environment,
    is_production_environment,
)


class ProtectedScopeEnvironment(BaseModel):
    class Config:
        arbitrary_types_allowed = True

    scopes: list[str] = []
    claims: dict[str, Any] = {}
    request: fastapi.Request


class ProtectedScopeOperation(Protocol):
    async def __call__(self, env: ProtectedScopeEnvironment) -> bool:
        ...


def or_(*args: ProtectedScopeOperation) -> ProtectedScopeOperation:
    async def composed_validation(env: ProtectedScopeEnvironment) -> bool:
        for arg in args:
            if await arg(env):
                return True
        return False

    return composed_validation


def and_(*args: ProtectedScopeOperation) -> ProtectedScopeOperation:
    async def composed_validation(env: ProtectedScopeEnvironment) -> bool:
        for arg in args:
            if not await arg(env):
                return False
        return True

    return composed_validation


def key_present(key_to_contain: str) -> ProtectedScopeOperation:
    async def any_with_key(env: ProtectedScopeEnvironment) -> bool:
        if key_to_contain in env.claims:
            return True
        logger.debug(
            "Failed to find key '%s' in JWT",
            key_to_contain,
            extra={"jwt_claims": env.claims},
        )
        return False

    return any_with_key


def key_contains_value(
    key_to_contain: str, value_to_contain: str
) -> ProtectedScopeOperation:
    async def any_with_key_and_value(env: ProtectedScopeEnvironment) -> bool:
        if (
            key_to_contain in env.claims
            and env.claims[key_to_contain] == value_to_contain
        ):
            return True
        logger.debug(
            "Failed to find key '%s' in JWT with the expected value '%s'",
            key_to_contain,
            value_to_contain,
            extra={"jwt_claims": env.claims},
        )
        return False

    return any_with_key_and_value


def key_contains_value_in_list(
    key_to_contain: str, list_of_possible_values_to_contain: list[str]
) -> ProtectedScopeOperation:
    async def any_with_key_in_value_list(env: ProtectedScopeEnvironment) -> bool:
        if (
            key_to_contain in env.claims
            and env.claims[key_to_contain] in list_of_possible_values_to_contain
        ):
            return True
        logger.debug(
            "Failed to find key '%s' in JWT with allowed value",
            key_to_contain,
            extra={
                "allowed_values": list_of_possible_values_to_contain,
                "jwt_claims": env.claims,
            },
        )
        return False

    return any_with_key_in_value_list


def scopes_present(required_scopes: Union[str, list[str]]) -> ProtectedScopeOperation:
    if isinstance(required_scopes, str):
        required_scopes = [required_scopes]  # wrap string in a list

    if not required_scopes:
        raise ValueError(
            "Endpoints protected with scopes_present must require at least one scope"
        )

    async def all_scopes_present(env: ProtectedScopeEnvironment) -> bool:
        jwt_scopes = env.scopes
        if not jwt_scopes:
            logger.debug("No scopes found in JWT claims")
            return False

        scopes_in_claims: bool = all(
            required_scope in jwt_scopes for required_scope in required_scopes
        )
        if not scopes_in_claims:
            missing_scopes: list[str] = list(set(required_scopes) - set(jwt_scopes))
            logger.debug("JWT is missing required scopes: %s", missing_scopes)
        return scopes_in_claims

    return all_scopes_present


def match_keys(**route_params: str) -> ProtectedScopeOperation:
    """For all key:value pairs in route_params we must have claims[key]==route_params[value]"""

    async def match_all_keys(env: ProtectedScopeEnvironment) -> bool:
        request: fastapi.Request
        # Loop over everything provided in the protected_route constructor
        # If claims_map is empty, they pass this validation stage
        for route_param_name, claim_field in route_params.items():

            # Check each key in protected_route matches a key in the request route
            if (
                route_param_name not in env.request.path_params
                or claim_field not in env.claims
            ):
                return False

            # Get the live value out of the request
            route_value: str = env.request.path_params[route_param_name]

            # Get the value out of the jwt_claims
            permission: str = env.claims[claim_field]

            # If the permission is a list, look in it. Otherwise just compare values
            if type(permission) == list:
                if route_value not in permission:
                    return False

            # Dicts aren't implemented yet
            elif type(permission) == dict:
                return False

            # Compare the route value and the claim
            elif route_value != permission:
                return False

        return True

    return match_all_keys


def non_production_only_route() -> ProtectedScopeOperation:
    async def non_production_only_route_internal(
        env: ProtectedScopeEnvironment,
    ) -> bool:
        return is_not_production_environment()

    return non_production_only_route_internal


def production_only_route() -> ProtectedScopeOperation:
    async def production_only_route_internal(env: ProtectedScopeEnvironment) -> bool:
        return is_production_environment()

    return production_only_route_internal


def argument_present(argument: str, expected_value: str) -> ProtectedScopeOperation:
    async def argument_present_internal(env: ProtectedScopeEnvironment) -> bool:
        value = env.request.query_params.get(argument, default="").upper()
        return value == expected_value.upper()

    return argument_present_internal


def argument_not_present(argument: str) -> ProtectedScopeOperation:
    async def argument_not_present_internal(env: ProtectedScopeEnvironment) -> bool:
        return env.request.query_params.get(argument, default=None) is None

    return argument_not_present_internal


def field_in_path_matches_jwt_claim(
    path_field_name: str, jwt_claim_name: str
) -> ProtectedScopeOperation:
    """
    Returns a function that checks that the named field in the request path matches the named JWT claim.
    :param path_field_name: Name of the field in the request path
    :param jwt_claim_name: Name of the JWT claim
    :return: a Callable
    """

    async def field_in_path_matches_jwt_claim_internal(
        env: ProtectedScopeEnvironment,
    ) -> bool:
        if (
            path_field_name not in env.request.path_params
            or jwt_claim_name not in env.claims
        ):
            return False
        uuid_in_path: Optional[str] = env.request.path_params[path_field_name]
        jwt_user_id: Optional[str] = env.claims[jwt_claim_name]
        return jwt_user_id is not None and uuid_in_path == jwt_user_id

    return field_in_path_matches_jwt_claim_internal


def field_in_body_matches_jwt_claim(
    body_field_name: str, jwt_claim_name: str
) -> ProtectedScopeOperation:
    """
    Returns a function that checks that the named field in the request JSON body matches the named JWT claim.
    :param body_field_name: Name of the field in the request body
    :param jwt_claim_name: Name of the JWT claim
    :return: a Callable
    """

    async def field_in_body_matches_jwt_claim_internal(
        env: ProtectedScopeEnvironment,
    ) -> bool:
        body = await env.request.json()
        field_in_body: Optional[str] = (
            body.get(body_field_name) if body is not None else None
        )
        jwt_claim: Optional[str] = env.claims.get(jwt_claim_name)
        return jwt_claim is not None and field_in_body == jwt_claim

    return field_in_body_matches_jwt_claim_internal
