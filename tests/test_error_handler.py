import logging
from typing import NoReturn

import pytest
from _pytest.logging import LogCaptureFixture
from fastapi import APIRouter, FastAPI
from httpx import AsyncClient

from fastapi_batteries_included.helpers.error_handler import (
    AuthMissingException,
    DuplicateResourceException,
    EntityNotFoundException,
    ServiceUnavailableException,
    UnprocessibleEntityException,
)

dummy_router = APIRouter()


@dummy_router.get("/entity_not_found")
async def entity_not_found_route() -> NoReturn:
    raise EntityNotFoundException


@dummy_router.get("/value_error")
async def value_error_route() -> NoReturn:
    raise ValueError


@dummy_router.get("/key_error")
async def key_error_route() -> NoReturn:
    raise KeyError(0)


@dummy_router.get("/duplicate_resource")
async def duplicate_resource_route() -> NoReturn:
    raise DuplicateResourceException


@dummy_router.get("/auth_missing")
async def auth_missing_route() -> NoReturn:
    raise AuthMissingException


@dummy_router.get("/permission")
async def permission_error_route() -> NoReturn:
    raise PermissionError


@dummy_router.get("/service_unavailable")
async def service_unavailable_route() -> NoReturn:
    raise ServiceUnavailableException


@dummy_router.get("/unprocessible_entity")
async def unprocessible_entity_route() -> NoReturn:
    raise UnprocessibleEntityException


class TestErrors:
    @pytest.fixture(scope="module")
    def app(self) -> FastAPI:
        "Single app with error endpoints is reused for each of these tests"
        from fastapi_batteries_included import create_app

        app = create_app(testing=True)
        app.include_router(dummy_router)
        return app

    @pytest.mark.parametrize(
        "url_path,expected_status,has_traceback",
        [
            ("/value_error", 400, True),
            ("/key_error", 500, True),
            ("/auth_missing", 401, False),
            ("/permission", 403, False),
            ("/entity_not_found", 404, False),
            ("/duplicate_resource", 409, True),
            ("/unprocessible_entity", 422, True),
            ("/service_unavailable", 503, True),
        ],
    )
    @pytest.mark.asyncio
    async def test_exception_handler(
        self,
        app: FastAPI,
        client: AsyncClient,
        caplog: LogCaptureFixture,
        url_path: str,
        expected_status: int,
        has_traceback: bool,
    ) -> None:
        with caplog.at_level(logging.DEBUG):
            response = await client.get(url_path)
        assert response.status_code == expected_status
        if has_traceback:
            assert "Traceback" in caplog.text
        else:
            assert "Traceback" not in caplog.text
