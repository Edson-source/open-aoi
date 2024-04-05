from typing import List

from sqlalchemy.orm import Session
from sqlalchemy import select

from open_aoi.models import engine, Base
from open_aoi.exceptions import IntegrityError


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
    def delete(cls, obj: Base):
        with Session(engine) as session:
            if cls.allow_delete_hook(session, obj.id):
                session.query(cls._model).filter(cls._model.id == obj.id).delete()
                session.commit()
                cls.post_delete_hook(obj)
            else:
                raise IntegrityError(
                    "Unable to delete. Object is a dependency for other objects."
                )

    @classmethod
    def delete_by_id(cls, id: int):
        with Session(engine) as session:
            if cls.allow_delete_hook(session, id):
                obj = cls.retrieve(id)
                session.query(cls._model).filter(cls._model.id == id).delete()
                session.commit()
                cls.post_delete_hook(obj)
            else:
                raise IntegrityError(
                    "Unable to delete. Object is a dependency for other objects."
                )

    @classmethod
    def list(cls) -> List[Base]:
        with Session(engine) as session:
            return session.query(cls._model).all()

    @classmethod
    def list_nested(cls) -> List[Base]:
        raise NotImplemented()

    @classmethod
    def create(cls, *args, **kwargs):
        raise NotImplemented()

    @classmethod
    def allow_delete_hook(cls, session: Session, id: int) -> bool:
        raise NotImplemented()

    @classmethod
    def post_delete_hook(cls, obj: Base):
        raise NotImplemented()
