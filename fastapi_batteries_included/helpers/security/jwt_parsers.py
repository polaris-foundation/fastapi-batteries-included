from typing import Any, Union

from jose import jwt as jose_jwt
from she_logging import logger

from fastapi_batteries_included.helpers.security import jwk
from fastapi_batteries_included.helpers.security.jwt import TokenData, jwt_settings


class JwtParser:
    title: str = "Base"

    def __init__(
        self,
        required_audience: str,
        required_issuer: str,
        allowed_algorithms: list[str],
        metadata_key: str = "",
        scope_key: str = "",
        verify: bool = True,
    ):
        self.required_audience: str = required_audience
        self.required_issuer: str = required_issuer
        self.allowed_algorithms: list[str] = allowed_algorithms
        self.metadata_key: str = metadata_key
        self.scope_key: str = scope_key
        self.decode_options: dict[
            str, Union[bool, int]
        ] = self._construct_verification_options(verify)

    def decode_jwt(self, jwt_token: str, unverified_header: dict) -> TokenData:
        raise NotImplementedError()

    def parse_access_token(self, access_token: dict) -> TokenData:

        # Custom claims
        if self.metadata_key in access_token:
            claims = self.extract_claims_from_token(access_token)
        else:
            claims = {}

        # Standard claims
        if "iss" in access_token:
            claims["iss"] = access_token["iss"]

        if "sub" in access_token:
            claims["sub"] = access_token["sub"]

        # Custom scopes/permissions
        if self.scope_key in access_token:
            raw_scopes = access_token[self.scope_key]
            if not isinstance(raw_scopes, str):
                raise PermissionError("Invalid scopes (must be string)")
            scopes: list[str] = access_token[self.scope_key].split(" ")
        else:
            scopes = []

        return TokenData(scopes=scopes, claims=claims)

    def extract_claims_from_token(self, access_token: dict) -> dict[str, Any]:
        claims: dict = {"raw": access_token}

        for claim in access_token[self.metadata_key]:
            if claim == "locations":
                # Special case
                claims["location_ids"] = [
                    location["id"]
                    for location in access_token[self.metadata_key][claim]
                ]
                continue
            claims[claim] = access_token[self.metadata_key][claim]

        return claims

    @staticmethod
    def _construct_verification_options(
        verify: bool,
    ) -> dict[str, Union[bool, int]]:
        return {
            "verify_signature": verify,
            "verify_aud": verify,
            "verify_iat": verify,
            "verify_exp": verify,
            "verify_nbf": verify,
            "verify_iss": verify,
            "verify_sub": verify,
            "verify_jti": verify,
            "leeway": 0,
        }

    def __str__(self) -> str:
        return "%s JwtParser with domain %s" % (self.title, self.required_issuer)


class InternalJwtParser(JwtParser):
    def __init__(
        self,
        required_audience: str,
        required_issuer: str,
        allowed_algorithms: list[str],
        metadata_key: str = "metadata",
        scope_key: str = "scope",
        verify: bool = True,
        hs_key: str = None,
        title: str = "Internal",
    ):
        self.title = title
        self.hs_key = hs_key
        super(InternalJwtParser, self).__init__(
            required_audience,
            required_issuer,
            allowed_algorithms,
            metadata_key,
            scope_key,
            verify,
        )

    def decode_jwt(self, jwt_token: str, unverified_header: dict) -> TokenData:
        access_token = jose_jwt.decode(
            jwt_token,
            self.hs_key,
            audience=self.required_audience,
            algorithms=self.allowed_algorithms,
            options=self.decode_options,
            issuer=self.required_issuer,
        )
        return self.parse_access_token(access_token)


class AuthProviderLoginJwtParser(JwtParser):
    title = "Auth0 login"

    def __init__(
        self,
        required_audience: str,
        required_issuer: str,
        allowed_algorithms: list[str],
        metadata_key: str = "",
        scope_key: str = "scope",
        verify: bool = True,
        hs_key: str = None,
    ):
        self.hs_key = hs_key
        super(AuthProviderLoginJwtParser, self).__init__(
            required_audience,
            required_issuer,
            allowed_algorithms,
            metadata_key,
            scope_key,
            verify,
        )

    def decode_jwt(self, jwt_token: str, unverified_header: dict) -> TokenData:
        access_token = jose_jwt.decode(
            jwt_token,
            self.hs_key,
            audience=self.required_audience,
            algorithms=self.allowed_algorithms,
            options=self.decode_options,
            issuer=self.required_issuer,
        )
        return self.parse_access_token(access_token)


class AuthProviderJwtParser(JwtParser):
    title = "Auth0 standard"

    def __init__(
        self,
        required_audience: str,
        required_issuer: str,
        allowed_algorithms: list[str],
        metadata_key: str = "",
        scope_key: str = "scope",
        verify: bool = True,
    ):
        super(AuthProviderJwtParser, self).__init__(
            required_audience,
            required_issuer,
            allowed_algorithms,
            metadata_key,
            scope_key,
            verify,
        )

    def decode_jwt(self, jwt_token: str, unverified_header: dict) -> TokenData:
        kid: str = unverified_header.get("kid", None)
        if kid is None:
            logger.warning("JWT provided with no kid field in header")
            raise ValueError("Could not retrieve JWT kid from header")

        rsa_key = jwk.retrieve_auth_provider_jwk(kid)

        if not rsa_key:
            logger.info("Could not retrieve JWT key from header: %s", unverified_header)
            raise ValueError("Could not retrieve JWT key from header")

        access_token = jose_jwt.decode(
            jwt_token,
            rsa_key,
            audience=self.required_audience,
            algorithms=self.allowed_algorithms,
            options=self.decode_options,
            issuer=self.required_issuer,
        )
        return self.parse_access_token(access_token)


def get_jwt_parser(token: str, verify: bool = True) -> JwtParser:
    full_auth_provider_domain = jwt_settings.AUTH_PROVIDER_DOMAIN
    full_customdb_auth_domain = jwt_settings.AUTH_PROVIDER_CUSTOM_DOMAIN
    full_internal_domain = jwt_settings.HS_ISSUER
    internal_audience: str = jwt_settings.HS_ISSUER

    algorithms = jwt_settings.VALID_JWT_ALGORITHMS

    # Find the appropriate issuer domain or error
    try:
        unverified_claims: dict = jose_jwt.get_unverified_claims(token)
    except jose_jwt.JWTError:
        raise ValueError("Failed to decode JWT claim")

    issuer = unverified_claims["iss"]
    if not issuer:
        raise ValueError("Detected JWT with no issuer")

    if issuer == full_auth_provider_domain:
        audience: str = jwt_settings.AUTH_PROVIDER_AUDIENCE
        metadata_key: str = jwt_settings.AUTH_PROVIDER_METADATA
        scope_key: str = jwt_settings.AUTH_PROVIDER_SCOPE_KEY

        jwt_parser: JwtParser = AuthProviderJwtParser(
            required_audience=audience,
            required_issuer=full_auth_provider_domain,
            allowed_algorithms=algorithms,
            metadata_key=metadata_key,
            scope_key=scope_key,
            verify=verify,
        )
    elif issuer == full_internal_domain:
        jwt_parser = InternalJwtParser(
            required_audience=internal_audience,
            required_issuer=full_internal_domain,
            allowed_algorithms=algorithms,
            metadata_key="metadata",
            scope_key="scope",
            verify=verify,
            hs_key=jwt_settings.HS_KEY,
        )
    elif issuer == full_customdb_auth_domain:
        jwt_parser = AuthProviderLoginJwtParser(
            required_audience=internal_audience,
            required_issuer=full_customdb_auth_domain,
            allowed_algorithms=algorithms,
            metadata_key="metadata",
            scope_key="scope",
            verify=verify,
            hs_key=jwt_settings.AUTH_PROVIDER_HS_KEY,
        )
    else:
        raise ValueError(f"Detected JWT with unknown issuer {issuer}")

    return jwt_parser
