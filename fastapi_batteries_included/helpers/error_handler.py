import sys
from collections.abc import Callable
from typing import Any, Optional, Union

from fastapi import FastAPI, Request
from she_logging import logger
from starlette.responses import JSONResponse


class EntityNotFoundException(Exception):
    pass


class ServiceUnavailableException(Exception):
    pass


class DuplicateResourceException(Exception):
    pass


class UnprocessibleEntityException(Exception):
    pass


class AuthMissingException(Exception):
    pass


def _catch(
    error: str,
    log_method: Callable,
    code: int,
    suppress_traceback: bool = False,
    original_exception: Optional[Exception] = None,
) -> JSONResponse:
    exc_info: Any = None
    if not suppress_traceback:
        if original_exception:
            exc_info = original_exception
        else:
            exc_info = sys.exc_info()

    log_method(str(error), exc_info=exc_info, stacklevel=2)

    return JSONResponse(
        status_code=code,
        content={"message": str(error)},
    )


def catch_database_exception(
    _error: Exception, msg: str = "Service unavailable"
) -> JSONResponse:
    return _catch(
        error=f"Database connection failed: {msg}",
        log_method=logger.critical,
        code=503,
        original_exception=_error,
    )


def catch_invalid_database_credentials(
    request: Request, error: Exception
) -> JSONResponse:
    return catch_database_exception(error, "Invalid credentials.")


def catch_invalid_database_uri(request: Request, error: Exception) -> JSONResponse:
    return catch_database_exception(error, "Invalid connection URI.")


def catch_bad_request(request: Request, error: Union[str, Exception]) -> JSONResponse:
    return _catch(
        str(error),
        logger.warning,
        400,
        original_exception=error if isinstance(error, Exception) else None,
    )


def catch_internal_error(request: Request, error: Exception) -> JSONResponse:
    return _catch(
        f"{type(error).__name__} {error}",
        logger.critical,
        500,
        original_exception=error,
    )


def catch_not_found(request: Request, error: Exception) -> JSONResponse:
    return _catch(str(error), logger.info, 404)


def catch_unauthorised(request: Request, _error: Exception) -> JSONResponse:
    # Suppress traceback because unauthorised is an invalid call, not an error
    return _catch("Forbidden", logger.info, 403, suppress_traceback=True)


def catch_not_implemented(request: Request, _error: Exception) -> JSONResponse:
    return _catch("Not implemented", logger.critical, 501, original_exception=_error)


def catch_unprocessible_entity(request: Request, _error: Exception) -> JSONResponse:
    return _catch("Unprocessible entity", logger.info, 422, original_exception=_error)


def catch_query_exception(request: Request, _error: Exception) -> JSONResponse:
    return _catch("Query error", logger.critical, 500, original_exception=_error)


def catch_service_unavailable(request: Request, _error: Exception) -> JSONResponse:
    return _catch(
        "Service unavailable", logger.critical, 503, original_exception=_error
    )


def catch_duplicate_resource_error(request: Request, error: Exception) -> JSONResponse:
    return _catch(str(error), logger.warning, 409, original_exception=error)


def catch_auth_missing_error(request: Request, _error: Exception) -> JSONResponse:
    return _catch("No authentication provided", logger.info, 401)


def catch_deflate_error(request: Request, error: Exception) -> JSONResponse:

    if "[^@]+@[^@]+\\.[^@]+" in str(error):
        return catch_bad_request(request, "email address format failed validation")

    if "Invalid choice:" in str(error):
        # Happens when an invalid choice (e.g. from a list of strings) is made on a property.
        return catch_bad_request(request, f"invalid choice for property {str(error)}")

    return catch_internal_error(request, error)


def init_error_handler(*, app: FastAPI, use_sqlalchemy: bool = False) -> None:

    # catch python errors
    app.exception_handler(ValueError)(catch_bad_request)
    app.exception_handler(KeyError)(catch_internal_error)
    app.exception_handler(TypeError)(catch_internal_error)
    app.exception_handler(PermissionError)(catch_unauthorised)
    app.exception_handler(NotImplementedError)(catch_not_implemented)

    # catch FastAPI Batteries Included errors
    app.exception_handler(EntityNotFoundException)(catch_not_found)
    app.exception_handler(ServiceUnavailableException)(catch_service_unavailable)
    app.exception_handler(UnprocessibleEntityException)(catch_unprocessible_entity)
    app.exception_handler(DuplicateResourceException)(catch_duplicate_resource_error)
    app.exception_handler(AuthMissingException)(catch_auth_missing_error)

    # catch SQLAlchemy errors, if installed
    if use_sqlalchemy:
        import sqlalchemy.exc
        from psycopg2 import ProgrammingError

        app.exception_handler(sqlalchemy.exc.ProgrammingError)(catch_query_exception)
        app.exception_handler(sqlalchemy.exc.OperationalError)(catch_database_exception)
        app.exception_handler(ProgrammingError)(catch_query_exception)
