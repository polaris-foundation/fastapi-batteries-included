from datetime import datetime, timezone
from typing import Any, Union

from fastapi import FastAPI
from fastapi_sqlalchemy import DBSessionMiddleware, db
from sqlalchemy import Column, MetaData, String, create_engine
from sqlalchemy.orm import Mapped, declarative_base, declarative_mixin
from sqlalchemy.types import DateTime

from fastapi_batteries_included.config import MsSQLDbSettings, PostgresDbSettings
from fastapi_batteries_included.helpers import generate_uuid

__all__ = ["db", "utcnow_with_timezone", "ModelIdentifier", "Base"]


def init_db(app: FastAPI, testing: bool = False) -> None:
    if app.state.use_mssql:
        settings: Union[PostgresDbSettings, MsSQLDbSettings] = MsSQLDbSettings()
    elif app.state.use_pgsql:
        settings = PostgresDbSettings()
    else:
        raise ValueError("App is not configured for a database")

    app.add_middleware(
        DBSessionMiddleware,
        db_url=settings.SQLALCHEMY_DATABASE_URI,
        engine_args=settings.SQLALCHEMY_ENGINE_OPTIONS,
    )

    metadata = MetaData()

    if testing:
        engine = create_engine(
            settings.SQLALCHEMY_DATABASE_URI, echo=settings.SQLALCHEMY_ECHO
        )
        metadata.create_all(engine)
        Base.metadata.create_all(engine)


def utcnow_with_timezone() -> datetime:
    return datetime.now(tz=timezone.utc)


Base: Any = declarative_base()


@declarative_mixin
class ModelIdentifier:
    uuid: Mapped[str] = Column(
        String(length=36),
        primary_key=True,
        default=generate_uuid,
        nullable=False,
    )
    created: Mapped[datetime] = Column(
        DateTime(timezone=True), default=utcnow_with_timezone, nullable=False
    )
    modified: Mapped[datetime] = Column(
        DateTime(timezone=True),
        default=utcnow_with_timezone,
        onupdate=utcnow_with_timezone,
        nullable=False,
    )

    def pack_identifier(self) -> dict[str, Any]:
        return {
            "uuid": self.uuid,
            "created": self.created,
            "modified": self.modified,
        }

    @staticmethod
    def schema() -> dict:
        raise NotImplementedError()
