from typing import Optional

from sqlalchemy import select

from open_aoi_core.controllers import Controller
from open_aoi_core.models import AccessorModel


class AccessorController(Controller):
    _model = AccessorModel

    # Aliases
    revoke_session_access = AccessorModel.revoke_session_access
    identify_session_accessor_id = AccessorModel.identify_session_accessor_id

    def retrieve_by_username(self, username: str) -> Optional[AccessorModel]:
        """Retrieve accessor entity by user name"""
        q = select(self._model).where(self._model.username == username)
        return self.session.scalars(q).one_or_none()

    def identify_session_accessor(self, storage: dict) -> AccessorModel:
        """Shorthand to retrieve accessor from session storage"""
        return self.retrieve(self.identify_session_accessor_id(storage))
