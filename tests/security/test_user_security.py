import logging

import pytest
from _pytest.logging import LogCaptureFixture
from fastapi import APIRouter, FastAPI, Security
from httpx import AsyncClient
from jose import jwt as jose_jwt

from fastapi_batteries_included.helpers.security.jwt_user import (
    ValidatedUser,
    get_validated_user,
)

dummy_router = APIRouter()


@dummy_router.get(
    "/secured_endpoint",
)
async def api_user_security(
    user: ValidatedUser = Security(get_validated_user, scopes=["hello:world"])
) -> dict:
    return {"user_id": user.user_id, "scopes": user.token_data.scopes}


@pytest.mark.asyncio
class TestApiKey:
    @pytest.fixture(scope="module")
    def app(self) -> FastAPI:
        "Single app with error endpoints is reused for each of these tests"
        from fastapi_batteries_included import create_app

        app = create_app(testing=True)
        app.include_router(dummy_router)
        return app

    @pytest.fixture
    def mock_bearer_authorization(self, jwt_scopes: str) -> dict:

        claims = {
            "sub": "1234567890",
            "name": "John Doe",
            "iat": 1_516_239_022,
            "iss": "http://localhost/",
            "scope": jwt_scopes,
            "metadata": {
                "clinician_id": "4321",
            },
        }
        token = jose_jwt.encode(claims, "secret", algorithm="HS256")
        return {"Authorization": f"Bearer {token}"}

    @pytest.mark.parametrize(
        "endpoint,jwt_scopes,expect_status",
        [
            ("/secured_endpoint", "foo:bar", 403),
            ("/secured_endpoint", "hello:world", 200),
        ],
    )
    async def test_protection(
        self,
        app: FastAPI,
        client: AsyncClient,
        caplog: LogCaptureFixture,
        mock_bearer_authorization: dict,
        endpoint: str,
        jwt_scopes: str,
        expect_status: int,
    ) -> None:
        with caplog.at_level(logging.DEBUG):
            response = await client.get(endpoint, headers=mock_bearer_authorization)

        assert response.status_code == expect_status

        log_records = [r for r in caplog.records if r.name != "asyncio"]
        if expect_status == 200:
            assert not log_records, "Expected no jwt logging on security success"
            assert response.json() == {
                "user_id": "1234567890",
                "scopes": jwt_scopes.split(" "),
            }
        else:
            assert "missing required scopes: ['hello:world']" in caplog.text
