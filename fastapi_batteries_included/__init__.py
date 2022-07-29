from typing import Any, Optional

from fastapi import FastAPI
from she_logging import logger
from she_logging.fastapi_request_id import RequestContextMiddleware

from .helpers.error_handler import init_error_handler
from .helpers.metrics import init_metrics
from .router_monitoring import init_monitoring


def create_app(
    testing: bool = False,
    use_pgsql: bool = False,
    use_mssql: bool = False,
    *,
    title: str = "FastAPI",
    description: str = "",
    version: str = "0.1.0",
    openapi_tags: Optional[list[dict[str, Any]]] = None,
    terms_of_service: Optional[str] = None,
    contact: Optional[dict[str, str]] = None,
    license_info: Optional[dict[str, str]] = None,
) -> FastAPI:

    app: FastAPI = FastAPI(
        title=title,
        description=description,
        version=version,
        openapi_tags=openapi_tags,
        terms_of_service=terms_of_service,
        contact=contact,
        license_info=license_info,
    )
    return augment_app(
        app=app,
        testing=testing,
        use_pgsql=use_pgsql,
        use_mssql=use_mssql,
    )


def augment_app(
    app: FastAPI,
    *,
    testing: bool = False,
    use_pgsql: bool = False,
    use_mssql: bool = False,
) -> FastAPI:
    app.state.use_pgsql = use_pgsql
    app.state.use_mssql = use_mssql

    # Register custom error handlers
    init_error_handler(app=app, use_sqlalchemy=use_pgsql or use_mssql)

    # Add in monitoring endpoints and metrics if not testing
    if not testing:
        init_monitoring(app)
        init_metrics(app)

    # Add in X-Request-ID handling
    app.add_middleware(RequestContextMiddleware)

    # Done!
    logger.info("App now includes batteries!")

    return app
