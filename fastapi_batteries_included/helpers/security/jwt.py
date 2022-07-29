from typing import Any, Optional

from jose import jwt as jose_jwt
from pydantic import BaseModel
from she_logging import logger

from fastapi_batteries_included import config

jwt_settings = config.JwtSettings()


class TokenData(BaseModel):
    scopes: list[str] = []
    claims: dict[str, Any] = {}


def current_jwt_user(token: TokenData) -> str:
    claims = token.claims

    for claim_type in jwt_settings.VALID_USER_ID_KEYS.intersection(claims.keys()):
        user_id = claims[claim_type]
        if isinstance(user_id, str):
            return user_id

    if claims:
        # There are claims, so we should expect to be able to get the user UUID.
        logger.warning("Could not get user UUID from JWT - claims are: %s", claims)
    return "unknown"


def decode_hs_jwt(
    hs_key: str, jwt_token: str, algorithms: list[str], decode_options: dict
) -> Optional[dict]:
    try:
        return jose_jwt.decode(
            jwt_token, hs_key, algorithms=algorithms, options=decode_options
        )
    except (jose_jwt.ExpiredSignatureError, jose_jwt.JWTError, jose_jwt.JWSError):
        logger.exception("Access attempted with incorrect JWT token: %s")
        # Deliberately mask the error so the caller has no clues about security internals
        return None
