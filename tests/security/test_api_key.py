import pytest
from fastapi import APIRouter, FastAPI, Response, Security, status
from httpx import AsyncClient

from fastapi_batteries_included.helpers.security.api_key import get_api_key

dummy_router = APIRouter()


@dummy_router.post(
    "/test_endpoint_1",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Security(get_api_key)],
)
async def api_key_security() -> Response:
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@pytest.mark.asyncio
class TestApiKey:
    @pytest.fixture(scope="module")
    def app(self) -> FastAPI:
        "Single app with error endpoints is reused for each of these tests"
        from fastapi_batteries_included import create_app

        app = create_app(testing=True)
        app.include_router(dummy_router)
        return app

    async def test_endpoint_success(
        self,
        app: FastAPI,
        client: AsyncClient,
    ) -> None:
        response = await client.post(
            f"/test_endpoint_1", headers={"X-Api-Key": "TopSecret"}
        )
        assert response.status_code == 204

    async def test_endpoint_401_no_header(
        self,
        app: FastAPI,
        client: AsyncClient,
    ) -> None:
        response = await client.post(f"/test_endpoint_1")
        assert response.status_code == 401

    async def test_endpoint_403_wrong_key(
        self,
        app: FastAPI,
        client: AsyncClient,
    ) -> None:
        response = await client.post(
            f"/test_endpoint_1", headers={"X-Api-Key": "incorrect"}
        )
        assert response.status_code == 403
