from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.openapi.models import HTTPBearer as HTTPBearerModel
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
    OAuth2,
    OAuth2PasswordBearer,
    OpenIdConnect,
    SecurityScopes,
)
from jose import jwt as jose_jwt
from pydantic import BaseModel
from she_logging import logger

from fastapi_batteries_included.helpers.security.jwt import TokenData, current_jwt_user
from fastapi_batteries_included.helpers.security.jwt_parsers import get_jwt_parser


class JWTBearer(OAuth2PasswordBearer):
    """FastAPI only puts security scheme scopes in the openapi if the bearer is OAuth2 or OpenIdConnect
    but we need the securityScheme set according to HTTPBearer. This class takes the behaviour of
    OAuth2PasswordBearer but uses the model from HTTPBearer to get the required openapi definition."""

    def __init__(
        self,
        *,
        description: Optional[str] = None,
        auto_error: bool = True,
    ):
        OAuth2PasswordBearer.__init__(
            self, tokenUrl="", scheme_name="bearerAuth", auto_error=auto_error
        )
        self.model = HTTPBearerModel(bearerFormat="JWT", description=description)


jwtbearer_scheme = JWTBearer()


class ValidatedUser(BaseModel):
    user_id: str
    token_data: TokenData


async def get_validated_jwt_token(
    security_scopes: SecurityScopes,
    jwt_token: str = Depends(jwtbearer_scheme),
) -> TokenData:
    try:
        jwt_parser = get_jwt_parser(jwt_token)
        unverified_header = jose_jwt.get_unverified_header(jwt_token)
        token_data = jwt_parser.decode_jwt(jwt_token, unverified_header)
    except (
        ValueError,
        jose_jwt.ExpiredSignatureError,
        jose_jwt.JWTClaimsError,
        jose_jwt.JWSError,
        jose_jwt.JWTError,
    ) as e:
        logger.info(
            "Access attempted with invalid JWT",
            extra={"error_message": e},
        )
        logger.debug("JWT value: %s", jwt_token)
        # Deliberately mask the error so the caller has no clues about security internals
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )

    scopes: Optional[list[str]] = security_scopes.scopes
    if scopes:
        required_scopes = set(scopes)
        missing_scopes = required_scopes - set(token_data.scopes)
        if missing_scopes:
            logger.debug("JWT is missing required scopes: %s", list(missing_scopes))
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions",
            )
    return token_data


async def get_validated_user(
    token_data: TokenData = Depends(get_validated_jwt_token),
) -> ValidatedUser:
    user = ValidatedUser(user_id=current_jwt_user(token_data), token_data=token_data)
    if user.user_id == "unknown":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    return user
