from sqlalchemy.orm import Session
from sqlalchemy import select

from open_aoi.controllers import Controller
from open_aoi.models import (
    AccessorModel,
)


class AccessorController(Controller):
    _model = AccessorModel
    revoke_session_access = AccessorModel.revoke_session_access
    identify_session_accessor_id = AccessorModel.identify_session_access

    @classmethod
    def retrieve_by_username(cls, username: str) -> AccessorModel:
        with Session(cls.engine) as session:
            q = select(cls._model).where(cls._model.username == username)
            res = session.scalars(q).one_or_none()
        return res

    @classmethod
    def identify_session_accessor(cls, storage: dict) -> AccessorModel:
        id = cls._model.identify_session_access(storage)
        return cls.retrieve(id)
