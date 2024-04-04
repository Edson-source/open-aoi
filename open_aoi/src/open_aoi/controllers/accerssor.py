from sqlalchemy.orm import Session
from sqlalchemy import select

from open_aoi.controllers import Controller
from open_aoi.models import (
    AccessorModel,
)


class AccessorController(Controller):
    model = AccessorModel

    @classmethod
    def select_by_username(cls, username: str) -> AccessorModel:
        with Session(cls.engine) as session:
            q = select(cls.model).where(cls.model.username == username)
            res = session.scalars(q).one_or_none()
        return res
