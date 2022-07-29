import logging

import pytest
from _pytest.logging import LogCaptureFixture
from fastapi import APIRouter, Depends, FastAPI
from httpx import AsyncClient

from fastapi_batteries_included.helpers.routes import deprecated_route

dummy_router = APIRouter()


@dummy_router.get(
    "/route/deprecated",
    deprecated=True,
    dependencies=[Depends(deprecated_route(superseded_by="GET /route/replacement"))],
)
async def route_deprecated() -> list:
    return []


@dummy_router.get("/route/replacement")
async def route_replacement() -> list:
    return []


class TestErrors:
    @pytest.fixture(scope="module")
    def app(self) -> FastAPI:
        "Single app with error endpoints is reused for each of these tests"
        from fastapi_batteries_included import create_app

        app = create_app(testing=True)
        app.include_router(dummy_router)
        return app

    @pytest.mark.asyncio
    async def test_deprecated_route(
        self,
        app: FastAPI,
        client: AsyncClient,
        caplog: LogCaptureFixture,
    ) -> None:
        with caplog.at_level(logging.DEBUG):
            response = await client.get("/route/deprecated")
        assert response.status_code == 200
        assert response.headers["Deprecation"] == "true"
        assert (
            response.headers["link"] == '</route/replacement>; rel="successor-version"'
        )

        assert (
            "Endpoint /route/deprecated is deprecated, use GET /route/replacement"
            in caplog.text
        )
