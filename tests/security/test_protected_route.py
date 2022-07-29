import logging
from unittest.mock import Mock

import pytest
from _pytest.fixtures import SubRequest
from _pytest.logging import LogCaptureFixture
from _pytest.monkeypatch import MonkeyPatch
from fastapi import APIRouter, FastAPI, Security
from starlette.testclient import TestClient

from fastapi_batteries_included import config
from fastapi_batteries_included.helpers.security import protected_route, protection
from fastapi_batteries_included.helpers.security.endpoint_security import scopes_present
from fastapi_batteries_included.helpers.security.jwt import jwt_settings

dummy_router = APIRouter()

protection.is_production_environment = lambda: False  # type:ignore


@dummy_router.get(
    "/secured_development",
    dependencies=[
        Security(protected_route(scopes_present(required_scopes="hello:world")))
    ],
)
def app_secured_development() -> dict:
    """Created in dev environment, tests can toggle security on/off"""
    return {"result": True}


protection.is_production_environment = lambda: True  # type:ignore


@dummy_router.get(
    "/secured_production",
    dependencies=[
        Security(protected_route(scopes_present(required_scopes="hello:world")))
    ],
)
def app_secured_production() -> dict:
    """Created in production environment, security is always enabled"""
    return {"result": True}


@dummy_router.get(
    "/scoped_endpoint",
    dependencies=[Security(protected_route(), scopes=["hello:world"])],
)
def app_scoped_endpoint() -> dict:
    """Openapi spec for this endpoint includes scopes."""
    return {"result": True}


protection.is_production_environment = config.is_production_environment


class TestProtectedRoutes:
    @pytest.fixture(scope="module")
    def app(self) -> FastAPI:
        "Single app with error endpoints is reused for each of these tests"
        from fastapi_batteries_included import create_app

        app = create_app(testing=True)
        app.include_router(dummy_router)
        return app

    @pytest.fixture
    def client(self, app: FastAPI) -> TestClient:
        client = TestClient(app)
        return client

    @pytest.fixture
    def mock_bearer_authorization(self, jwt_scopes: str) -> dict:
        from jose import jwt

        claims = {
            "sub": "1234567890",
            "name": "John Doe",
            "iat": 1_516_239_022,
            "iss": "http://localhost/",
            "scope": jwt_scopes,
        }
        token = jwt.encode(claims, "secret", algorithm="HS256")
        return {"Authorization": f"Bearer {token}"}

    @pytest.fixture
    def ignore_validation(self, request: SubRequest, monkeypatch: MonkeyPatch) -> bool:
        monkeypatch.setattr(jwt_settings, "IGNORE_JWT_VALIDATION", request.param)
        return request.param

    @pytest.mark.parametrize(
        "endpoint,ignore_validation,jwt_scopes,expect_status",
        [
            ("/secured_development", True, "foo:bar", 200),
            ("/secured_development", False, "foo:bar", 403),
            ("/secured_development", True, "hello:world", 200),
            ("/secured_development", False, "hello:world", 200),
            ("/secured_production", True, "foo:bar", 403),
            ("/secured_production", False, "foo:bar", 403),
            ("/secured_production", True, "hello:world", 200),
            ("/secured_production", False, "hello:world", 200),
            ("/scoped_endpoint", True, "foo:bar", 403),
            ("/scoped_endpoint", False, "foo:bar", 403),
            ("/scoped_endpoint", True, "hello:world", 200),
            ("/scoped_endpoint", False, "hello:world", 200),
        ],
        indirect=["ignore_validation"],
    )
    def test_protection(
        self,
        client: TestClient,
        caplog: LogCaptureFixture,
        mock_bearer_authorization: Mock,
        endpoint: str,
        ignore_validation: bool,
        jwt_scopes: str,
        expect_status: int,
    ) -> None:
        with caplog.at_level(logging.DEBUG):
            response = client.get(endpoint, headers=mock_bearer_authorization)

        assert response.status_code == expect_status

        log_records = [r for r in caplog.records if r.name != "asyncio"]
        if expect_status == 200 and not ignore_validation:
            assert not log_records, "Expected no jwt logging on security success"

        if expect_status == 200:
            assert response.json() == {"result": True}
        else:
            assert "missing required scopes: ['hello:world']" in caplog.text

    def test_bearer_auth(self, app: FastAPI) -> None:
        openapi_spec = app.openapi()
        security_schemes: dict = openapi_spec["components"]["securitySchemes"]
        assert security_schemes == {
            "bearerAuth": {"bearerFormat": "JWT", "scheme": "bearer", "type": "http"}
        }
        assert openapi_spec["paths"]["/secured_production"]["get"]["security"] == [
            {"bearerAuth": []}
        ]
        assert openapi_spec["paths"]["/secured_development"]["get"]["security"] == [
            {"bearerAuth": []}
        ]
        assert openapi_spec["paths"]["/scoped_endpoint"]["get"]["security"] == [
            {"bearerAuth": ["hello:world"]}
        ]
