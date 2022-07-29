import urllib
from functools import lru_cache
from typing import Optional, Union

from pydantic import BaseSettings, Field, validator
from pydantic.fields import ModelField


def _not_allowed_in_production(
    flag: bool, values: dict[str, str], field: ModelField
) -> bool:
    if is_production_environment(environment=values["ENVIRONMENT"]) and flag:
        raise ValueError(
            f"{field.name} cannot be True if ENVIRONMENT is set to PRODUCTION."
        )
    return flag


class GeneralSettings(BaseSettings):
    ENVIRONMENT: str = "PRODUCTION"
    ALLOW_DROP_DATA: bool = False
    DEBUG: bool = False
    LISTEN_ADDRESS: str = "0.0.0.0"
    LOG_REQUEST_ID_GENERATE_IF_NOT_FOUND: bool = True
    PORT: int = 5000
    PREFERRED_URL_SCHEME: str = "http"
    UNITTESTING: bool = False

    class Config:
        case_sensitive = True

    _validate_allow_drop_data = validator("ALLOW_DROP_DATA", allow_reuse=True)(
        _not_allowed_in_production
    )


class JwtSettings(GeneralSettings):
    HS_KEY: str
    AUTH_PROVIDER_JWKS_URL: str
    AUTH_PROVIDER_JWKS_TESTING: str = ""

    AUTH_PROVIDER_DOMAIN: Optional[str] = None
    AUTH_PROVIDER_AUDIENCE: str = ""
    AUTH_PROVIDER_METADATA: str = ""
    AUTH_PROVIDER_SCOPE_KEY: str = "permissions"

    AUTH_PROVIDER_CUSTOM_DOMAIN: Optional[str] = None
    AUTH_PROVIDER_HS_KEY: Optional[str] = None
    JWKS_CACHE_EXPIRY_SECONDS: int = 3600
    JWKS_CACHE_SIZE: int = 10

    IGNORE_JWT_VALIDATION: bool = False
    PROXY_URL: str
    HS_ISSUER: str = ""
    VALID_JWT_ALGORITHMS: list[str] = [
        "HS256",
        "HS512",
        "HS384",
        "RS256",
        "RS384",
        "RS512",
        "ES256",
        "ES384",
        "ES512",
    ]
    VALID_USER_ID_KEYS: set[str] = {"sub"}

    @validator("HS_ISSUER")
    def issuer_default_to_proxy_url(
        cls, v: str, values: dict[str, str], **kwargs: object
    ) -> str:
        if not v:
            v = values.get("PROXY_URL", "").rstrip("/") + "/"
        return v

    _validate_ignore_jwt_validation = validator(
        "IGNORE_JWT_VALIDATION", allow_reuse=True
    )(_not_allowed_in_production)


class ApiKeySettings(BaseSettings):
    ACCEPTED_API_KEY: str


class SqlDbSettings(BaseSettings):
    DATABASE_USER: str
    DATABASE_PASSWORD: str
    DATABASE_HOST: str
    DATABASE_PORT: int
    DATABASE_NAME: str
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    SQLALCHEMY_ECHO: bool = False

    max_overflow: int = Field(env="SQLALCHEMY_MAX_OVERFLOW", default=0)
    pool_size: int = Field(env="SQLALCHEMY_POOL_SIZE", default=2)
    pool_timeout: int = Field(env="SQLALCHEMY_POOL_TIMEOUT", default=30)
    pool_recycle: int = Field(env="SQLALCHEMY_POOL_RECYCLE", default=600)
    pool_pre_ping: bool = Field(env="SQLALCHEMY_POOL_PRE_PING", default=True)


class PostgresDbSettings(SqlDbSettings):
    """SQL database config for Postgres"""

    SQLALCHEMY_DATABASE_URI: str = ""

    executemany_mode: str = Field(env="SQLALCHEMY_EXECUTEMANY_MODE", default="values")
    SQLALCHEMY_ENGINE_OPTIONS: dict = Field(default_factory=dict)

    @validator("SQLALCHEMY_ENGINE_OPTIONS")
    def build_engine_options(
        cls, v: dict, values: dict[str, Union[str, int, bool]]
    ) -> dict:
        if not v:
            v = {
                "max_overflow": values["max_overflow"],
                "pool_size": values["pool_size"],
                "pool_timeout": values["pool_timeout"],
                "pool_recycle": values["pool_recycle"],
                "pool_pre_ping": values["pool_pre_ping"],
                "executemany_mode": values["executemany_mode"],
            }
        return v

    @validator("SQLALCHEMY_DATABASE_URI")
    def build_database_uri(cls, v: str, values: dict[str, Union[int, str]]) -> str:
        if not v:
            db_user = values["DATABASE_USER"]
            db_pass = values["DATABASE_PASSWORD"]
            db_host = values["DATABASE_HOST"]
            db_port = values["DATABASE_PORT"]
            db_name = values["DATABASE_NAME"]
            v = f"postgresql+psycopg2://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
        return v


class MsSQLDbSettings(SqlDbSettings):
    ODBC_DRIVER: str = "ODBC Driver 17 for SQL Server"
    SQLALCHEMY_DATABASE_URI: str = ""

    @validator("SQLALCHEMY_DATABASE_URI")
    def build_database_uri(cls, v: str, values: dict[str, Union[int, str]]) -> str:
        if not v:
            db_user = values["DATABASE_USER"]
            db_pass = values["DATABASE_PASSWORD"]
            db_host = values["DATABASE_HOST"]
            db_port = values["DATABASE_PORT"]
            db_name = values["DATABASE_NAME"]
            odbc_driver: str = str(values["ODBC_DRIVER"])
            odbc_driver_escaped = urllib.parse.quote_plus(odbc_driver)

            v = f"mssql+pyodbc://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}?driver={odbc_driver_escaped}"
        return v

    SQLALCHEMY_ENGINE_OPTIONS: dict = Field(default_factory=dict)

    @validator("SQLALCHEMY_ENGINE_OPTIONS")
    def build_engine_options(
        cls, v: dict, values: dict[str, Union[str, int, bool]]
    ) -> dict:
        if not v:
            v = {
                "max_overflow": values["max_overflow"],
                "pool_size": values["pool_size"],
                "pool_timeout": values["pool_timeout"],
                "pool_recycle": values["pool_recycle"],
                "pool_pre_ping": values["pool_pre_ping"],
            }
        return v


@lru_cache
def is_production_environment(environment: str = None) -> bool:
    if environment is None:
        environment = GeneralSettings().ENVIRONMENT

    return environment not in ("DEMO", "DEVELOPMENT", "STAGING", "TRAINING", "TEST")


@lru_cache
def is_not_production_environment(environment: str = None) -> bool:
    return not is_production_environment(environment=environment)
