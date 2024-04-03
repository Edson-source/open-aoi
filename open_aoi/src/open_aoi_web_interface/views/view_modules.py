import logging
from typing import Optional
from uuid import uuid4

from nicegui import ui
from fastapi.responses import RedirectResponse
from PIL import Image

from open_aoi.exceptions import AuthException
from open_aoi.models import AccessorModel, TemplateModel
from open_aoi_web_interface.views.common import (
    inject_header,
    ACCESS_PAGE,
    access_guard,
)

logger = logging.getLogger("ui.devices")


def _handle_trigger_inspection():
    pass


def _handle_update_image():
    pass


def view() -> Optional[RedirectResponse]:
    try:
        accessor = access_guard()
    except AuthException:
        return RedirectResponse(ACCESS_PAGE)

    inject_header()

    with ui.column().classes("w-full"):
        ui.label("Modules")
        ui.upload(
            on_upload=lambda e: ui.notify(f"Uploaded {e.name}"), max_files=1
        ).classes("max-w-full")
