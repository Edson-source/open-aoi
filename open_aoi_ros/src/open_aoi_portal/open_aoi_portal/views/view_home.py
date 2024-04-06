import logging
from typing import Optional

from rclpy.node import Node
from fastapi.responses import RedirectResponse

from open_aoi.exceptions import AuthException
from open_aoi_portal.views.common import (
    inject_header,
    ACCESS_PAGE,
    access_guard,
)

logger = logging.getLogger("ui.home")


def get_view(node: Node):
    def view() -> Optional[RedirectResponse]:
        try:
            access_guard()
        except AuthException:
            return RedirectResponse(ACCESS_PAGE)

        inject_header()

    return view
