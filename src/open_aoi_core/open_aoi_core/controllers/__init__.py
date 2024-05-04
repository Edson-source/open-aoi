"""
    Controllers are meant to manipulate with database records. Controller is related to database model and should encapsulate complex logic.
    Common operations like retrieve by id, list, delete, etc are defined by root controller. Other model specific operations
    should be defined by each concrete controller. Controller does not perform commit operation.
    ```
        controller = Controller(session)
        controller.delete(entity)
        controller.commit()  # Resp. `session.commit()`
    ```
"""

from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import select

from open_aoi_core.models import Base
from open_aoi_core.exceptions import SystemIntegrityException


class Controller:
    """Basic controller class"""

    _model: Base  # Related model

    def __init__(self, session: Session):
        self.session = session

    def retrieve(self, id: int) -> Optional[Base]:
        """Retrieve single record by id. If no records found None is returned (same if more than one record exist)"""

        q = select(self._model).where(self._model.id == id)
        return self.session.scalars(q).one_or_none()

    def delete(self, entity: Base):
        """
        Delete provided entity after this operation was allowed (to keep database integrity some controllers will prevent deletion)
        - raise: SystemIntegrityException if delete operation was not allowed.
        """

        if self.allow_delete_hook(entity.id):
            self.session.query(self._model).filter(self._model.id == entity.id).delete()
            self.post_delete_hook(entity)
        else:
            raise SystemIntegrityException(
                "Unable to delete. Object is a dependency for other objects."
            )

    def delete_by_id(self, id: int):
        """
        Delete entity by id after this operation was allowed (to keep database integrity some controllers will prevent deletion)
        - raise: SystemIntegrityException if id was not found or delete operation was not allowed.
        """

        if self.allow_delete_hook(id):
            entity = self.retrieve(id)
            try:
                assert entity is not None
            except AssertionError as e:
                raise SystemIntegrityException(
                    "Unable to delete entity. Entity was not found."
                )
            self.session.query(self._model).filter(self._model.id == id).delete()
            self.post_delete_hook(entity)
        else:
            raise SystemIntegrityException(
                "Unable to delete. Object is a dependency for other objects."
            )

    def commit(self):
        """Alias to session.commit()"""
        self.session.commit()

    def list(self) -> List[Base]:
        """Return list of entities"""
        return self.session.query(self._model).all()

    def list_nested(self) -> List[Base]:
        """Return list of entities with related sub models allowing nested properties access: model.sub_model.property"""
        raise NotImplementedError()

    def create(self, *args, **kwargs):
        """Create entity"""
        raise NotImplementedError()

    def allow_delete_hook(self, id: int) -> bool:
        """Hook that is called before deleting the model. Should return False to prevent delete operation."""
        return True

    def post_delete_hook(self, obj: Base):
        """Hook that is called after delete operation (successful)"""
        pass
