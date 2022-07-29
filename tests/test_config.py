import pytest
from _pytest.monkeypatch import MonkeyPatch


class TestConfig:
    def test_init_jwt_config_success(
        self, monkeypatch: MonkeyPatch, clear_caches: None
    ) -> None:
        from fastapi_batteries_included.config import JwtSettings

        monkeypatch.setenv("HS_KEY", "key_test")
        monkeypatch.setenv("PROXY_URL", "http://someurl.com/")
        monkeypatch.delenv("HS_ISSUER", raising=False)

        settings = JwtSettings()

        assert settings.HS_KEY == "key_test"
        assert settings.PROXY_URL == "http://someurl.com/"
        assert settings.HS_ISSUER == "http://someurl.com/"

    def test_init_jwt_config_missing(
        self, monkeypatch: MonkeyPatch, clear_caches: None
    ) -> None:
        from fastapi_batteries_included.config import JwtSettings

        monkeypatch.delenv("HS_KEY")
        monkeypatch.delenv("PROXY_URL")

        with pytest.raises(ValueError):
            JwtSettings()

    def test_jwt_production(self, monkeypatch: MonkeyPatch, clear_caches: None) -> None:
        from fastapi_batteries_included.config import JwtSettings

        monkeypatch.setenv("ENVIRONMENT", "PRODUCTION")
        monkeypatch.setenv("IGNORE_JWT_VALIDATION", "true")

        with pytest.raises(ValueError):
            JwtSettings()

    def test_init_jwt_config_not_required(
        self, monkeypatch: MonkeyPatch, clear_caches: None
    ) -> None:
        from fastapi_batteries_included.config import GeneralSettings

        monkeypatch.delenv("HS_KEY")
        monkeypatch.delenv("PROXY_URL")

        settings = GeneralSettings()
        assert settings.LOG_REQUEST_ID_GENERATE_IF_NOT_FOUND is True

    @pytest.mark.parametrize(
        "environment,expected",
        [("PRODUCTION", True), ("DEVELOPMENT", False), (None, True)],
    )
    def test_production_environment(
        self,
        monkeypatch: MonkeyPatch,
        clear_caches: None,
        environment: str,
        expected: bool,
    ) -> None:
        from fastapi_batteries_included.config import (
            is_not_production_environment,
            is_production_environment,
        )

        if environment is None:
            monkeypatch.delenv("ENVIRONMENT", raising=False)
        else:
            monkeypatch.setenv("ENVIRONMENT", environment)

        assert is_production_environment() is expected
        assert is_not_production_environment() is not expected
