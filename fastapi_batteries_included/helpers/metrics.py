import time

from fastapi import Depends, FastAPI, Request, Response
from fastapi.responses import PlainTextResponse
from prometheus_client import Counter, Histogram, Summary, generate_latest
from prometheus_fastapi_instrumentator import Instrumentator
from she_logging import logger
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

REQUEST_LATENCY = Histogram(
    "fastapi_request_latency_seconds", "FastAPI Request Latency", ["method", "url"]
)

REQUEST_COUNT = Counter(
    "fastapi_request_count", "FastAPI Request Count", ["method", "url", "http_status"]
)

REQUEST_TIME = Summary(
    "request_processing_seconds",
    "Time spent processing request",
    ["method", "endpoint"],
)


class NoMetrics:
    def __init__(self, request: Request) -> None:
        request.state.enable_metrics = False


def set_no_metrics(request: Request) -> None:
    request.state.enable_metrics = False


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        start_time = time.time()
        request.state.enable_metrics = True
        response = await call_next(request)
        return after_request(start_time, request, response)


def add_no_cache_headers(response: Response) -> Response:
    """
    Add headers to both force IE to not cache response
    Only add header if not already set
    """
    if not response.headers.get("Cache-Control"):
        response.headers["Cache-Control"] = "no-cache, must-revalidate"
    if not response.headers.get("Pragma"):
        response.headers["Pragma"] = "no-cache"
    if not response.headers.get("Expires"):
        response.headers["Expires"] = "0"
    return response


def after_request(start_time: float, request: Request, response: Response) -> Response:
    response = add_no_cache_headers(response)

    # Skip logging and metrics for app monitoring probes
    if not request.state.enable_metrics:
        return response

    request_latency: float = time.time() - start_time
    endpoint = request.base_url
    REQUEST_LATENCY.labels(request.method, endpoint).observe(request_latency)
    REQUEST_COUNT.labels(request.method, endpoint, response.status_code).inc()
    REQUEST_TIME.labels(request.method, endpoint).observe(request_latency)

    content_length = response.headers.get("content-length")

    request_details = {
        "status": response.status_code,
        "requestUrl": str(request.url),
        "requestMethod": request.method,
        "remoteIp": request.client.host if request.client else None,
        "responseSize": content_length,
        "userAgent": str(request.headers.get("User-Agent", None)),
        "latency": f"{request_latency:.4f}s",
    }
    additional_details = {
        "requestXHeaders": {
            k: v for k, v in request.headers.items() if k.lower().startswith("x-")
        },
        "requestQueryParams": dict(request.query_params or {}),
        "requestPathParams": dict(request.path_params or {}),
    }
    additional_details = {k: v for k, v in additional_details.items() if v}
    additional_detail_keys = {item for v in additional_details.values() for item in v}
    logger.info(
        '%s "%s" %s',
        request.method,
        request.url,
        response.status_code,
        extra={"httpRequest": request_details},
    )
    if additional_detail_keys:
        logger.debug(
            "Request has additional details %s",
            ", ".join(additional_detail_keys),
            extra={"httpRequest": additional_details},
        )
    return response


def init_metrics(app: FastAPI) -> None:
    Instrumentator().instrument(app)
    app.add_middleware(MetricsMiddleware)

    @app.get(
        "/metrics",
        response_class=PlainTextResponse,
        dependencies=[Depends(set_no_metrics)],
        include_in_schema=False,
    )
    def get_metrics() -> bytes:
        return generate_latest()

    logger.debug("Registered metrics route on /metrics")
