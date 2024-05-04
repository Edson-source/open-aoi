import logging
from typing import Optional

from nicegui import app
from fastapi.responses import RedirectResponse

from open_aoi_core.services import StandardClient
from open_aoi_core.controllers.accessor import AccessorController
from open_aoi_core.exceptions import AuthenticationException
from open_aoi_portal.common import (
    inject_header,
    get_session,
    ACCESS_PAGE,
)

logger = logging.getLogger("ui.home")


def get_view(node: StandardClient):
    def view() -> Optional[RedirectResponse]:
        session = get_session()
        accessor_controller = AccessorController(session)
        try:
            accessor = accessor_controller.identify_session_accessor(app.storage.user)
            assert accessor.role.allow_system_view
        except (AssertionError, AuthenticationException):
            accessor_controller.revoke_session_access(app.storage.user)
            return RedirectResponse(ACCESS_PAGE)
        inject_header(accessor)

    return view
