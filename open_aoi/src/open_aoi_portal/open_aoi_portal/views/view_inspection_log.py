import logging
from typing import Optional
from uuid import uuid4

from PIL import Image
from nicegui import ui, app
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from open_aoi_core.exceptions import AuthException
from open_aoi_core.controllers.accessor import AccessorController
from open_aoi_core.models import TITLE_LIMIT, DESCRIPTION_LIMIT, AccessorModel, TemplateModel
from open_aoi_portal.common import (
    inject_header,
    ACCESS_PAGE,
    get_session,
)
from open_aoi_portal.settings import INSPECTION_LIVE_LOG_DEPTH

logger = logging.getLogger("ui.devices")

im = "/home/egor/Downloads/drawcore_ocr_damaged.bmp"
im = Image.open(im)


def _handle_trigger_inspection():
    pass


def _handle_update_image():
    pass


def view() -> Optional[RedirectResponse]:
    session = get_session()
    access_controller = AccessorController(session)
    try:
        access_controller.identify_session_accessor(app.storage.user)
    except AuthException:
        return RedirectResponse(ACCESS_PAGE)

    inject_header()

    with ui.grid(columns=2).classes("w-full"):
        with ui.column():
            ui.label("Inspection")
            ii = ui.interactive_image(im)

            with ui.row().classes("w-full"):
                with ui.column():
                    ui.label("PCB")
                    ui.label("Test")
                    ui.label("Test")

        with ui.column():
            ui.label("Results")
            columns = [
                {
                    "name": "timestamp",
                    "label": "Timestamp",
                    "field": "timestamp",
                    "required": True,
                    "align": "left",
                },
                {
                    "name": "code",
                    "label": "Code",
                    "field": "code",
                    "required": True,
                    "align": "left",
                },
                {
                    "name": "log",
                    "label": "Log",
                    "field": "log",
                    "required": True,
                    "align": "left",
                },
                {
                    "name": "result",
                    "label": "Result",
                    "field": "result",
                    "required": True,
                    "align": "left",
                },
                {
                    "name": "url",
                    "label": "URL",
                    "field": "url",
                    "required": True,
                    "align": "left",
                },
            ]
            rows = [
                {
                    "timestamp": "123",
                    "code": "pcb123",
                    "log": "its dead",
                    "result": False,
                    "url": "123",
                },
            ]
            t = ui.table(columns=columns, rows=rows, row_key="name").classes("w-full")
            t.rows.append(
                {
                    "timestamp": "123",
                    "code": "pcb123",
                    "log": "its dead",
                    "result": False,
                    "url": "123",
                }
            )
