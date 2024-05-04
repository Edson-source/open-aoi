import logging
from typing import Optional

from nicegui import app
from rclpy.node import Node
from fastapi.responses import RedirectResponse

from open_aoi_core.controllers.accessor import AccessorController
from open_aoi_core.exceptions import AuthenticationException
from open_aoi_portal.common import (
    inject_header,
    get_session,
    ACCESS_PAGE,
)

logger = logging.getLogger("ui.home")


def get_view(node: Node):
    def view() -> Optional[RedirectResponse]:
        session = get_session()
        access_controller = AccessorController(session)
        try:
            access_controller.identify_session_accessor(app.storage.user)
        except AuthenticationException:
            return RedirectResponse(ACCESS_PAGE)

        inject_header()

    return view
