# FastAPI Batteries Included

An installable package for API microservices. It provides FastAPI plus the basic extras we need for every API microservice.

FastAPI Batteries Included contains the following functionality:
* Common configuration
* Database setup (PostgreSQL)
* Monitoring API endpoints, and metrics
* Endpoint security and JWT parsing
* API error handling

To use FastAI=PI Batteries Included, call `augment_app`, passing in the FastAPI app as a parameter.

```python
def create_app() -> FastAPI:
    app: FastAPI = FastAPI(title="Test App")
    
    # Augment app to initialise FastAPI Batteries Included.
    app = fbi_augment_app(app=app)

    # Add a router of your choice.
    app.include_router(some_router)
    return app
```

Pre-requisites for development
------------------------------

You must install the Microsoft ODBC drivers before the tests can run.

For MacOS:

```shell
brew tap microsoft/mssql-release https://github.com/Microsoft/homebrew-mssql-release
brew update
HOMEBREW_NO_ENV_FILTERING=1 ACCEPT_EULA=Y brew install msodbcsql17 mssql-tools
```

If you need to uninstall the ODBC driver:
```shell
odbcinst -u -d -n "ODBC Driver 17 for SQL Server"
```

For Linux see https://docs.microsoft.com/en-us/sql/connect/odbc/linux-mac/installing-the-microsoft-odbc-driver-for-sql-server

## Maintainers
The Polaris platform was created by Sensyne Health Ltd., and has now been made open-source. As a result, some of the
instructions, setup and configuration will no longer be relevant to third party contributors. For example, some of
the libraries used may not be publicly available, or docker images may not be accessible externally. In addition, 
CICD pipelines may no longer function.

For now, Sensyne Health Ltd. and its employees are the maintainers of this repository.

## Common configuration
Depending on the flags you pass into the `fbi_augment_app` call, initialising the config will check for the presence
of certain sets of environment variables (defaulting where appropriate). Each set of environment variables is grouped
into classes in [fastapi_batteries_included/config.py](fastapi_batteries_included/config.py)

## Database setup (PostgreSQL)
Use the `init_db(app)` function in [fastapi_batteries_included/sqldb.py](fastapi_batteries_included/sqldb.py) to initialise
a SQL database. This also provides utility functions, and a base `Identifer` model for the `SQLAlchemy` ORM.

## Monitoring API endpoints, and metrics
Augmenting an app with FastAPI Batteries included will register a blueprint for monitoring endpoints, which can be found 
in [fastapi_batteries_included/router_monitoring/\_\_init__.py](fastapi_batteries_included/router_monitoring/__init__.py).
The `/running` endpoint is useful for Kubernetes readiness and liveness checks, as well as healthchecks within docker
environments.

There is additional logic in [fastapi_batteries_included/helpers/metrics.py](fastapi_batteries_included/helpers/metrics.py)
that add performance metrics and logging via middleware. This allows you to see information about requests
and responses in the form of logging and response headers.

## Endpoint security and JWT Parsing

Several options are available to provide endpoint security.

### API Key

```python
@router.post(
    "/endpoint/path",
    dependencies=[Security(get_api_key)],
)
async def api_key_security() -> Response:
    ...
```
The caller must pass the header `X-Api-Key` set to the same value as given in the
environment variable ACCEPTED_API_KEY. If the header does not match the response is
`403 Forbidden`.

### JWT tokens with specified scopes

JWT is an optional extra in fastapi-batteries-included. Install with `extras=jwt` if you want jwt support.

For the simplest case where an endpoint requires a validated JWT token and required scopes all present:
```python
from fastapi_batteries_included.helpers.security.jwt_user import get_validated_jwt_token


@router.get(
    "/endpoint/path",
    dependencies=[Security(get_validated_jwt_token, scopes=["hello:world"])]
)
async def api_user_security() -> Response:
    ...
```
The caller must pass a valid JWT as a bearer token in the Authorisation header and
all scopes in the security declaration must be present in the user's jwt. If these conditions
are not met the response is '403 Forbidden'.

If the user's scopes or claims are required for further processing in the endpoint use:

```python
from fastapi_batteries_included.helpers.security.jwt_user import ValidatedUser, get_validated_jwt_token


@router.get("/endpoint/path")
async def api_user_security(get_validated_jwt_token: TokenData = Security(get_validated_jwt_token, scopes=["hello:world"])) -> Response:
    ...
```


If the user id is also required you can use `get_validated_user` instead. If no userid is found or the scopes do not
match this will result in a 403 response:
```python
from fastapi_batteries_included.helpers.security.jwt_user import get_validated_user


@router.get("/endpoint/path")
async def api_user_security(user: ValidatedUser = Security(get_validated_user, scopes=["hello:world"])) -> Response:
    logger,info("User is %s", user.user_id)
```

The `get_validated_jwt_token` and `get_validated_user` functions should only be used as a security dependency, you
should not call them directly.

JWT providers are set using the following environment variables:

### Protected routes

If the simple user with scopes is not sufficient use the `protected_route` dependency.

```python
from fastapi_batteries_included.helpers.security import protected_route

@router.get(
    "/endpoint/path",
    dependencies=[Security(protected_route(
        or_(
            scopes_present(required_scopes="write:gdm_location"),
            scopes_present(required_scopes="write:send_location"),
            scopes_present(required_scopes="write:location"),
        )))]
)
async def api_user_security() -> Response:
    ...
```
This form allows access to the endpoint if any of the specified scopes is available.
You may also include the `scopes` parameter when using `protected_route`:

```python
from fastapi_batteries_included.helpers.security import protected_route

@router.get(
    "/endpoint/path",
    dependencies=[Security(protected_route(), scopes="write:location")]
)
async def api_user_security() -> Response:
    ...
```
The `scopes=` parameter is an additional check roughly equivalent to using `protected_route` with a single call to 
`scopes_present`. Where possible use `scopes=` as that will include the required scopes in the openapi documentation.
Note you can override `scopes_present` in development mode by setting `IGNORE_JWT_VALIDATION` but the checking for 
`scopes=` may not be overridden.

`protected_route` parameters are `validation_function: ProtectedScopeOperation` and 
`allowed_issuers: Union[list[Optional[str]], str, None]`. The `verify` flag and additional keyword arguments present
in the Flask equivalent function are not implemented for FastAPI.

Endpoint security functions that may be used on a `protected_route` are:

* `or_(...)`
* `and_(...)`
* `scopes_present(required_scopes=...)`
* `key_present(...)`
* `key_contains_value(...)`
* `key_contains_value_in_list(...)`
* `match_keys(...)`
* `non_production_only_route(...)`
* `production_only_route(...)`
* `argument_present(...)`
* `argument_not_present(...)`
* `field_in_path_matches_jwt_claim(...)`
* `field_in_body_matches_jwt_claim(...)`

N.B. the `compare_keys` function in the Flask implementation is not implemented here.

## API error handling
This library extends the default FastAPI error handling to allow more specific HTTP error codes and messages to be 
returned when certain exceptions are raised. This error handling can be found in
[fastapi_batteries_included/helpers/error_handler.py](fastapi_batteries_included/helpers/error_handler.py). For example,
raising a `PermissionError` will result in an HTTP 403 error response.
