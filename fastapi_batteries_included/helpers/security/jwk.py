import json
from typing import Any, Optional, TypedDict

import httpx
from cachetools import TTLCache, cached
from she_logging import logger

from fastapi_batteries_included.helpers.security.jwt import jwt_settings


class JwkCollection(TypedDict):
    keys: list[dict[str, Any]]


jwk_cache: TTLCache = TTLCache(
    maxsize=jwt_settings.JWKS_CACHE_SIZE, ttl=jwt_settings.JWKS_CACHE_EXPIRY_SECONDS
)


@cached(cache=jwk_cache)
def fetch_auth_provider_jwks(key_id: str = "") -> dict:
    """Returns keys in a { kid: jwk} map."""

    url = jwt_settings.AUTH_PROVIDER_JWKS_URL
    logger.debug("Fetching JWKS from %s", url)
    with httpx.Client() as client:
        fresh_jwks_resp = client.get(url)
    if fresh_jwks_resp.status_code != 200:
        logger.critical(f"Not able to retrieve Auth JWKS from %s", url)
        raise EnvironmentError(f"Could not retrieve JWKs from {url}")
    jwks: JwkCollection = fresh_jwks_resp.json()

    keys = {jwk["kid"]: jwk for jwk in jwks["keys"]}
    return keys


def retrieve_auth_provider_jwk(key_id: str, testing: bool = False) -> Optional[dict]:
    if testing:
        jwks_str = jwt_settings.AUTH_PROVIDER_JWKS_TESTING
        jwks = json.loads(jwks_str)
        return jwks

    jwks = fetch_auth_provider_jwks()
    return jwks.get(key_id)
