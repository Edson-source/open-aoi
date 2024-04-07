import logging
from typing import Optional
from uuid import uuid4

from PIL import Image
from nicegui import ui, app
from fastapi.responses import RedirectResponse

from open_aoi.exceptions import AuthException
from open_aoi.controllers import TemplateController
from open_aoi.controllers.accessor import AccessorController
from open_aoi.models import TITLE_LIMIT, AccessorModel, TemplateModel
from open_aoi_portal.views.common import (
    inject_header,
    get_session,
    ACCESS_PAGE,
)

logger = logging.getLogger("ui.devices")

im = "/home/egor/Downloads/drawcore_ocr_damaged.bmp"
im = Image.open(im)


def _handle_create_template(
    title_input: ui.input, image: Image, accessor: AccessorModel, callback: callable
):
    try:
        assert title_input.validate()
    except AssertionError:
        ui.notify("Required values are missing", type="negative")
        return

    # TODO: upload blob
    image_blob = str(uuid4())
    try:
        TemplateController.create(title_input.value.strip(), image_blob, accessor)
    except Exception as e:
        logger.exception(e)
        ui.notify("Failed to create template")
        return
    ui.notify(f"Template {title_input.value.strip()} created!", type="positive")
    callback()


def _handle_delete_template(template: TemplateModel, callback: callable):
    TemplateController.delete(template)
    callback()


def _handle_take_picture():
    pass


def view(template_id: Optional[int] = None) -> Optional[RedirectResponse]:
    session = get_session()
    access_controller = AccessorController(session)
    try:
        accessor = access_controller.identify_session_accessor(app.storage.user)
    except AuthException:
        return RedirectResponse(ACCESS_PAGE)

    inject_header()

    with ui.grid(columns=2).classes("w-full"):
        with ui.column():
            ui.label("Template configuration")
            template_title = ui.input(
                label="Template title",
                placeholder=f"Enter any value... [{TITLE_LIMIT}]",
                on_change=lambda e: template_title_display.set_text(
                    f"[{len(template_title.value.strip())}/{TITLE_LIMIT}] {template_title.value.strip()}"
                ),
                validation={
                    "Title is too long": lambda value: len(value.strip())
                    <= TITLE_LIMIT,
                    "Title is too short": lambda value: len(value.strip()) != 0,
                },
            ).classes("w-full")
            template_title_display = ui.label("").classes("text-secondary")

            with ui.row().classes("w-full"):
                ui.space()
                ui.button(
                    "Save",
                    on_click=lambda: _handle_create_template(
                        template_title, im, accessor, generate_template_list
                    ),
                )

            with ui.grid(columns=4).classes("w-full"):
                ui.image(im).classes("col-span-3")
                with ui.scroll_area().classes("col-span-1"):
                    ui.image(im).classes()
                    ui.image(im).classes()

        with ui.column():
            # TODO: provide image navigation
            with ui.interactive_image(im) as ii:
                ui.button("Take picture").classes("absolute bottom-0 right-0 m-2")

    ui.label("Registered templates")
    template_list_container = ui.list().classes("w-full").props("dense")

    # TODO: confirm delete
    def generate_template_list():
        template_list_container.clear()
        template_list = TemplateController.list()

        with template_list_container:
            for template in template_list:
                with ui.item().props("clickable"):
                    with ui.item_section():
                        with ui.row():
                            ui.label(template.title)
                            ui.space()
                            ui.button(
                                "Edit",
                            ).props("size=sm")
                            ui.button(
                                "Remove",
                                color="negative",
                                on_click=lambda: _handle_delete_template(
                                    template, generate_template_list
                                ),
                            ).props("size=sm")

    generate_template_list()
