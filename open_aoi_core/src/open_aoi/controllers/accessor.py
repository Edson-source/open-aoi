from sqlalchemy import select

from open_aoi.controllers import Controller
from open_aoi.models import (
    AccessorModel,
)


class AccessorController(Controller):
    _model = AccessorModel
    revoke_session_access = AccessorModel.revoke_session_access
    identify_session_accessor_id = AccessorModel.identify_session_access

    def retrieve_by_username(self, username: str) -> AccessorModel:
        q = select(self._model).where(self._model.username == username)
        res = self.session.scalars(q).one_or_none()
        return res

    def identify_session_accessor(self, storage: dict) -> AccessorModel:
        id = self._model.identify_session_access(storage)
        return self.retrieve(id)
