import uuid
from datetime import datetime

import freezegun
import pytest
from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from fastapi.security import (
    OAuth2PasswordBearer,
    OAuth2PasswordRequestForm,
    SecurityScopes,
)
from fastapi_sqlalchemy.middleware import DBSessionMeta
from sqlalchemy import Column, String

from fastapi_batteries_included.sqldb import Base, ModelIdentifier


class Entity(ModelIdentifier, Base):
    __tablename__ = "entity"
    dummy = Column(String(), nullable=False, unique=False)

    def to_dict(self) -> dict:
        return {
            "uuid": self.uuid,
            "created": self.created,
            "modified": self.modified,
            "dummy": self.dummy,
        }


ORIGINAL_TIME = "2021-07-29T09:00:00+00:00"
UPDATE_TIME = "2021-08-29T12:34:45+00:00"


@pytest.mark.freeze_time(ORIGINAL_TIME)
def test_identifier(
    app: FastAPI, db: DBSessionMeta, freezer: freezegun.api.StepTickTimeFactory
) -> None:
    """
    Tests that when a database entity is updated, the modified field is set automatically.
    """
    test_entity = Entity(dummy="first_value")
    db.session.add(test_entity)
    db.session.commit()

    assert test_entity.created.isoformat() == ORIGINAL_TIME
    assert test_entity.modified.isoformat() == ORIGINAL_TIME

    freezer.move_to(UPDATE_TIME)

    assert test_entity.uuid is not None
    as_uuid: uuid.UUID = uuid.UUID(test_entity.uuid)
    assert str(as_uuid) == test_entity.uuid

    assert test_entity.dummy == "first_value"

    test_entity.dummy = "second_value"
    db.session.commit()

    updated_created: datetime = test_entity.created
    updated_modified: datetime = test_entity.modified
    assert test_entity.created.isoformat() == ORIGINAL_TIME
    assert test_entity.modified.isoformat() == UPDATE_TIME

    assert test_entity.dummy == "second_value"

    as_json: dict = jsonable_encoder(test_entity.to_dict())

    assert as_json == {
        "created": ORIGINAL_TIME,
        "modified": UPDATE_TIME,
        "dummy": "second_value",
        "uuid": str(as_uuid),
    }
