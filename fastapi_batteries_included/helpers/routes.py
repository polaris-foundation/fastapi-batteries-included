from datetime import datetime, timezone
from typing import Callable

from fastapi import Request, Response
from she_logging import logger


def deprecated_route(
    superseded_by: str = None, deprecated: datetime = None
) -> Callable:
    """
    Dependency to be used to mark deprecated endpoints.
    It sets the Deprecation header in all responses to the `deprecated` time, or `true` if no time was given
    and link header to the successor endpoint (if given)

    N.B. This is an addition to the `deprecated` parameter on the route decorator that
    must still be set to mark the route depractaed in the openapi.

    :param superseded_by: method and path of the new endpoint that should be used
    :param deprecated: when the endpoint became deprecated (may be in the future)

    Usage example:
    @router.get(
        "/oldroute",
        deprecated=True,
        dependencies=[Depends(deprecated_route(superseded_by="GET /newroute"))],
    )
    async def old_route() -> Response:
        ...
    """
    if deprecated and deprecated.tzinfo is None:
        deprecated = deprecated.replace(tzinfo=timezone.utc)

    deprecation_header: str = (
        deprecated.isoformat(timespec="milliseconds") if deprecated else "true"
    )
    if superseded_by:
        successor_method, successor = superseded_by.split(maxsplit=1)
        link = f'<{successor}>; rel="successor-version"'
    else:
        link = ""

    def deprecation_dependency(request: Request, response: Response) -> None:
        logger.warning(
            "Endpoint %s is deprecated, use %s",
            request.url.path,
            superseded_by,
        )

        response.headers["Deprecation"] = deprecation_header
        if link:
            response.headers["Link"] = link

    return deprecation_dependency
