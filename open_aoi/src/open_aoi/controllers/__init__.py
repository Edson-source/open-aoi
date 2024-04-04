from typing import List

from sqlalchemy.orm import Session
from sqlalchemy import select

from open_aoi.models import engine, Base


class Controller:
    _model: Base
    engine = engine

    @classmethod
    def retrieve(cls, id: int) -> Base:
        with Session(engine) as session:
            q = select(cls._model).where(cls._model.id == id)
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
            q = select(cls._model).where(cls._model.id == id).one()
            session.delete(q)
            session.commit()

    @classmethod
    def list(cls) -> List[Base]:
        with Session(engine) as session:
            q = select(cls._model)
            res = session.scalars(q).all()
        return res

    @classmethod
    def create(cls, *args, **kwargs):
        raise NotImplemented()
