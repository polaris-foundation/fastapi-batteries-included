import logging
from typing import Any, Optional, Type

import pytest
from _pytest.logging import LogCaptureFixture
from fastapi import FastAPI
from httpx import AsyncClient, Response
from prometheus_fastapi_instrumentator import Instrumentator
from pytest_mock import MockFixture


class _Anything:
    def __init__(self, _type: Optional[Type] = None) -> None:
        self._type = _type

    def __eq__(self, other: Any) -> bool:
        if self._type is not None:
            return isinstance(other, self._type)
        return True


ANY = _Anything()
ANY_STRING = _Anything(str)
ANY_FLOAT = _Anything(float)


class TestMonitoring:
    @pytest.fixture
    def no_httpx_logs(self) -> None:
        import logging

        logger = logging.getLogger("httpx")
        logger.setLevel(logging.WARNING)

    @pytest.fixture
    def app(self, mocker: MockFixture) -> FastAPI:
        from fastapi_batteries_included import create_app

        # p-f-i doesn't like being attached to multiple apps so stub it out
        mocker.patch.object(Instrumentator, "instrument")

        app = create_app(testing=False, use_pgsql=True)
        return app

    @pytest.mark.parametrize(
        "endpoint, content_type,expected",
        [
            ("/running", "application/json", {"running": True}),
            (
                "/version",
                "application/json",
                {"circle": ANY_STRING, "hash": ANY_STRING},
            ),
            ("/metrics", "text/plain", None),
        ],
    )
    @pytest.mark.asyncio
    async def test_monitoring_endpoints(
        self,
        client: AsyncClient,
        no_httpx_logs: None,
        caplog: LogCaptureFixture,
        endpoint: str,
        content_type: str,
        expected: dict,
    ) -> None:
        with caplog.at_level(logging.DEBUG):
            response: Response = await client.get(endpoint)

        assert not caplog.text, "Metrics endpoint should not be logged"
        assert response.status_code == 200
        if content_type == "application/json":
            assert response.json() == expected
