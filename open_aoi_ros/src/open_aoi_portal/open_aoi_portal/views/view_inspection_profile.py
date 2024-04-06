import logging
from typing import Optional

from nicegui import ui
from fastapi.responses import RedirectResponse
from PIL import Image

from open_aoi.exceptions import AuthException
from open_aoi.controllers import (
    CameraController,
    TemplateController,
    InspectionProfileController,
)
from open_aoi.models import TITLE_LIMIT, DESCRIPTION_LIMIT, CODE_LIMIT, TemplateModel
from open_aoi_web_interface.views.common import (
    inject_header,
    ACCESS_PAGE,
    access_guard,
)

logger = logging.getLogger("ui.inspection_profile")

im = "/home/egor/Downloads/drawcore_ocr_damaged.bmp"
im = Image.open(im)


def _handle_create_profile(
    profile_title,
    profile_description,
    camera_select,
    pcb_uid,
    accessor,
):
    pass


def view(profile_id: Optional[int] = None) -> Optional[RedirectResponse]:
    try:
        accessor = access_guard()
    except AuthException:
        return RedirectResponse(ACCESS_PAGE)

    inject_header()

    camera_list = dict([(obj.id, obj.title) for obj in CameraController.list()])
    template_list = dict([(obj.id, obj.title) for obj in TemplateController.list()])

    with ui.column().classes("w-full"):
        ui.label("Inspection profile")
        profile_title = ui.input(
            label="Profile title",
            placeholder=f"Enter any value... [{TITLE_LIMIT}]",
            on_change=lambda e: profile_title_display.set_text(
                f"[{len(profile_title.value.strip())}/{TITLE_LIMIT}] {profile_title.value.strip()}"
            ),
            validation={
                "Title is too long": lambda value: len(value.strip()) <= TITLE_LIMIT,
                "Title is too short": lambda value: len(value.strip()) != 0,
            },
        ).classes("w-full")
        profile_title_display = ui.label("").classes("text-secondary")

        profile_description = ui.input(
            label="Profile description",
            placeholder=f"Enter any value... [{DESCRIPTION_LIMIT}]",
            on_change=lambda e: profile_description_display.set_text(
                f"[{len(profile_description.value.strip())}/{DESCRIPTION_LIMIT}] {profile_description.value.strip()}"
            ),
            validation={
                "Description is too long": lambda value: len(value.strip())
                <= DESCRIPTION_LIMIT,
                "Description is too short": lambda value: len(value.strip()) != 0,
            },
        ).classes("w-full")
        profile_description_display = ui.label("").classes("text-secondary")

        camera_select = ui.select(
            camera_list,
            label="Camera",
            clearable=True,
            validation={"Camera is required": lambda value: value is not None},
        ).classes("w-full")

        pcb_uid = ui.input(
            label="PCB identification",
            placeholder=f"Enter PCB code value... [{CODE_LIMIT}]",
            on_change=lambda e: pcb_uid_display.set_text(
                f"[{len(pcb_uid.value.strip())}/{CODE_LIMIT}] {pcb_uid.value.strip()}"
            ),
            validation={
                "Identification is too long": lambda value: len(value.strip())
                <= CODE_LIMIT,
                "Identification is too short": lambda value: len(value.strip()) != 0,
            },
        ).classes("w-full")
        pcb_uid_display = ui.label("").classes("text-secondary")
        template_select = ui.select(
            template_list,
            label="Template",
            clearable=True,
            validation={"Template is required": lambda value: value is not None},
        ).classes("w-full")
        with ui.grid(columns=3).classes("w-full"):
            template_preview = ui.image(im)
            ui.label("Some info about template")

        with ui.row().classes("w-full"):
            ui.space()
            ui.button(
                "Save",
                on_click=lambda: _handle_create_profile(
                    profile_title,
                    profile_description,
                    camera_select,
                    pcb_uid,
                    template_select,
                    accessor,
                ),
            )

    ui.label("Registered profiles")
    profile_list_container = ui.list().classes("w-full").props("dense")

    def generate_profile_list():
        profile_list_container.clear()
        profile_list = InspectionProfileController.list()
        if len(profile_list):
            with profile_list_container:
                for profile in profile_list:
                    with ui.item().props("clickable"):
                        with ui.item_section():
                            with ui.row():
                                ui.label(f"{profile.title}. {profile.description[:20]}")
                                ui.space()
                                ui.button(
                                    "Activate",
                                ).props("size=sm")
                                ui.button(
                                    "Edit",
                                ).props("size=sm")
                                ui.button(
                                    "Remove",
                                    color="negative",
                                ).props("size=sm")

    generate_profile_list()
