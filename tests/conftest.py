import os
from typing import Any, AsyncGenerator, Generator

import pytest
import pytest_asyncio
from _pytest.monkeypatch import MonkeyPatch
from fastapi import FastAPI
from fastapi_sqlalchemy.middleware import DBSessionMeta
from httpx import AsyncClient

from fastapi_batteries_included import sqldb


@pytest.fixture
def use_pgsql() -> bool:
    return os.environ.get("RUN_POSTGRES_TESTS", "").lower() == "true"


@pytest.fixture
def use_mssql() -> bool:
    return os.environ.get("RUN_MSSQL_TESTS", "").lower() == "true"


@pytest.fixture(autouse=True)
def database_config(monkeypatch: MonkeyPatch, use_pgsql: bool, use_mssql: bool) -> None:
    if use_mssql:
        monkeypatch.setenv("DATABASE_PORT", os.environ["MSSQL_1433_TCP_PORT"])
        monkeypatch.setenv("DATABASE_HOST", os.environ["MSSQL_HOST"])
    if use_pgsql:
        monkeypatch.setenv("DATABASE_PORT", os.environ["PGSQL_5432_TCP_PORT"])
        monkeypatch.setenv("DATABASE_HOST", os.environ["PGSQL_HOST"])


@pytest.fixture
def app(use_pgsql: bool, use_mssql: bool) -> FastAPI:
    """Fixture that creates app for testing"""
    from fastapi_batteries_included import create_app

    app = create_app(testing=True, use_pgsql=use_pgsql, use_mssql=use_mssql)
    if use_pgsql or use_mssql:
        sqldb.init_db(app, testing=True)
    return app


@pytest.fixture
def db(app: FastAPI) -> Generator[DBSessionMeta, None, None]:
    from fastapi_batteries_included.sqldb import db as fbi_db

    with fbi_db():
        yield fbi_db


@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture(autouse=True)
def clear_caches() -> None:
    from fastapi_batteries_included import config
    from fastapi_batteries_included.helpers.security import jwk

    v: Any
    for v in vars(config).values():
        if hasattr(v, "cache_clear"):
            v.cache_clear()

    jwk.jwk_cache.clear()
