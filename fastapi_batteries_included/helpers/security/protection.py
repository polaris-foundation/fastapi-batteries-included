from typing import Optional, Union

from fastapi import Depends
from starlette.requests import Request

from fastapi_batteries_included.config import is_production_environment
from fastapi_batteries_included.helpers.security.endpoint_security import (
    ProtectedScopeEnvironment,
    ProtectedScopeOperation,
    match_keys,
)
from fastapi_batteries_included.helpers.security.jwt import TokenData, jwt_settings
from fastapi_batteries_included.helpers.security.jwt_user import (
    ValidatedUser,
    get_validated_jwt_token,
    get_validated_user,
)


class _ProtectedRoute:
    allowed_issuers: set[str]
    validation_function: ProtectedScopeOperation
    hs_key: Optional[str] = None

    def __init__(
        self,
        validation_function: ProtectedScopeOperation = None,
        allowed_issuers: Union[list[Optional[str]], str, None] = None,
    ) -> None:
        self.hs_key: Optional[str] = None

        # allowed_issuers is allowed to be a string or a list of strings
        if isinstance(allowed_issuers, str):
            self.allowed_issuers = set(allowed_issuers)
        elif allowed_issuers is None:
            self.allowed_issuers = set()
        else:
            self.allowed_issuers = {a for a in allowed_issuers if a}

        self.validation_function = validation_function or match_keys()

    async def __call__(
        self, request: Request, token_data: TokenData = Depends(get_validated_jwt_token)
    ) -> None:
        env = ProtectedScopeEnvironment(
            scopes=token_data.scopes, claims=token_data.claims, request=request
        )
        valid = await self.validation_function(env)

        if not valid:
            raise PermissionError(
                f"Claims {str(env.claims)} not valid for call to {env.request.url}"
            )


class _ProtectedRouteDevelopment(_ProtectedRoute):
    async def __call__(
        self, request: Request, token_data: TokenData = Depends(get_validated_jwt_token)
    ) -> None:
        env = ProtectedScopeEnvironment(
            scopes=token_data.scopes, claims=token_data.claims, request=request
        )
        valid = await self.validation_function(env)

        if not valid and not jwt_settings.IGNORE_JWT_VALIDATION:
            raise PermissionError(
                f"Claims {str(env.claims)} not valid for call to {env.request.url}"
            )


def protected_route(
    validation_function: ProtectedScopeOperation = None,
    allowed_issuers: Union[list[Optional[str]], str, None] = None,
) -> _ProtectedRoute:
    if is_production_environment():
        return _ProtectedRoute(validation_function, allowed_issuers)
    else:
        return _ProtectedRouteDevelopment(validation_function, allowed_issuers)
