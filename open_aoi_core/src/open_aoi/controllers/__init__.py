from typing import List

from sqlalchemy.orm import Session
from sqlalchemy import select

from open_aoi.models import Base
from open_aoi.exceptions import IntegrityError


class Controller:
    _model: Base

    def __init__(self, session: Session):
        self.session = session

    def retrieve(self, id: int) -> Base:
        q = select(self._model).where(self._model.id == id)
        res = self.session.scalars(q).one_or_none()
        return res

    def delete(self, obj: Base):
        if self.allow_delete_hook(obj.id):
            self.session.query(self._model).filter(self._model.id == obj.id).delete()
            self.post_delete_hook(obj)
        else:
            raise IntegrityError(
                "Unable to delete. Object is a dependency for other objects."
            )

    def delete_by_id(self, id: int):
        if self.allow_delete_hook(id):
            obj = self.retrieve(id)
            self.session.query(self._model).filter(self._model.id == id).delete()
            self.post_delete_hook(obj)
        else:
            raise IntegrityError(
                "Unable to delete. Object is a dependency for other objects."
            )

    def commit(self):
        self.session.commit()

    def list(self) -> List[Base]:
        return self.session.query(self._model).all()

    def list_nested(self) -> List[Base]:
        raise NotImplementedError()

    def create(self, *args, **kwargs):
        raise NotImplementedError()

    def allow_delete_hook(self, id: int) -> bool:
        raise NotImplementedError()

    def post_delete_hook(self, obj: Base):
        pass
