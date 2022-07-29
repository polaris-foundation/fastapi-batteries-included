import re

import pytest
from _pytest.logging import LogCaptureFixture
from fastapi import APIRouter, FastAPI
from httpx import AsyncClient
from prometheus_fastapi_instrumentator import Instrumentator
from pytest_mock import MockFixture

from fastapi_batteries_included import init_metrics

dummy_router = APIRouter()


@dummy_router.get("/hello-world")
async def hello_world() -> dict:
    return {"greeting": "hello"}


class TestErrors:
    @pytest.fixture
    def app(self, mocker: MockFixture) -> FastAPI:
        "Single app with error endpoints is reused for each of these tests"
        from fastapi_batteries_included import create_app

        # p-f-i doesn't like being attached to multiple apps so stub it out
        mocker.patch.object(Instrumentator, "instrument")

        app = create_app(testing=True)
        app.include_router(dummy_router)
        init_metrics(app)
        return app

    @pytest.mark.asyncio
    async def test_metrics_with_xheaders(
        self, app: FastAPI, client: AsyncClient, caplog: LogCaptureFixture
    ) -> None:
        response = await client.get("/hello-world", headers={"X-Hello": "World"})
        assert response.status_code == 200
        assert response.json() == {"greeting": "hello"}
        expected = """INFO.*?GET "http://test/hello-world" 200\nDEBUG.*?Request has additional details"""
        assert re.match(expected, caplog.text)

    @pytest.mark.asyncio
    async def test_metrics_no_xheaders(
        self, app: FastAPI, client: AsyncClient, caplog: LogCaptureFixture
    ) -> None:
        response = await client.get("/hello-world")
        assert response.status_code == 200
        assert response.json() == {"greeting": "hello"}
        expected = """INFO.*?GET "http://test/hello-world" 200\nDEBUG"""
        assert re.match(expected, caplog.text)
        assert "Request has additional details" not in caplog.text
