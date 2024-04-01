from typing import List
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import select

from open_aoi.models import (
    engine,
    Base,
    CameraModel,
    TemplateModel,
    AccessorModel,
    InspectionProfileModel,
)


class Controller:
    model: Base
    engine = engine

    @classmethod
    def retrieve(cls, id: int) -> Base:
        with Session(engine) as session:
            q = select(cls.model).where(cls.model.id == id)
            res = session.scalars(q).one_or_none()
        return res

    @classmethod
    def delete(cls, obj: Base) -> Base:
        with Session(engine) as session:
            session.delete(obj)
            session.commit()

    @classmethod
    def delete_by_id(cls, id: int) -> Base:
        with Session(engine) as session:
            q = select(cls.model).where(cls.model.id == id).one()
            session.delete(q)
            session.commit()

    @classmethod
    def list(cls) -> List[Base]:
        with Session(engine) as session:
            q = select(cls.model)
            res = session.scalars(q).all()
        return res

    @classmethod
    def create(cls, *args, **kwargs):
        raise NotImplemented()


class CameraController(Controller):
    model = CameraModel

    @classmethod
    def create(
        cls, title: str, description: str, ip_address: str, accessor: AccessorModel
    ) -> CameraModel:
        with Session(engine) as session:
            obj = CameraModel(
                title=title,
                description=description,
                ip_address=ip_address,
                created_by=accessor,
                created_at=datetime.now(),
            )
            session.add(obj)
            session.commit()
            return obj


class AccessorController(Controller):
    model = AccessorModel

    @classmethod
    def select_by_username(cls, username: str) -> AccessorModel:
        with Session(engine) as session:
            q = select(cls.model).where(cls.model.username == username)
            res = session.scalars(q).one_or_none()
        return res


class TemplateController(Controller):
    model = TemplateModel


class InspectionProfileController(Controller):
    model = InspectionProfileModel
