import logging
from typing import Optional

from nicegui import ui
from fastapi.responses import RedirectResponse
from PIL import Image

from open_aoi.exceptions import AuthException
from open_aoi.controllers import CameraController
from open_aoi.models import TITLE_LIMIT, DESCRIPTION_LIMIT, AccessorModel, CameraModel
from open_aoi_web_interface.views.common import (
    inject_header,
    ACCESS_PAGE,
    access_guard,
)

logger = logging.getLogger("ui.devices")


def _handle_create_camera(
    title_input: ui.input,
    description_input: ui.input,
    ip_address_input: ui.input,
    accessor: AccessorModel,
    callback,
):
    try:
        assert title_input.validate()
        assert description_input.validate()
        assert ip_address_input.validate()
    except AssertionError:
        ui.notify("Required values are missing")
        return

    try:
        CameraController.create(
            title=title_input.value.strip(),
            description=description_input.value.strip(),
            ip_address=ip_address_input.value.strip(),
            accessor=accessor,
        )
    except Exception as e:
        logger.exception(e)
        ui.notify("Failed to create camera")
        return
    ui.notify(f"Camera {title_input.value.strip()} created!", type="positive")
    callback()


def _handle_delete_camera(camera: CameraModel, callback):
    CameraController.delete(camera)
    callback()


def view() -> Optional[RedirectResponse]:
    try:
        accessor = access_guard()
    except AuthException:
        return RedirectResponse(ACCESS_PAGE)

    inject_header()

    with ui.grid(columns=2).classes("w-full"):
        with ui.column():
            ui.label("Camera configuration")
            camera_title = ui.input(
                label="Camera title",
                placeholder=f"Enter any value... [{TITLE_LIMIT}]",
                on_change=lambda e: camera_title_display.set_text(
                    f"[{len(camera_title.value)}/{TITLE_LIMIT}] {camera_title.value}"
                ),
                validation={
                    "Title is too long": lambda value: len(value) <= TITLE_LIMIT,
                    "Title is too short": lambda value: len(value.strip()) != 0,
                },
            ).classes("w-full")
            camera_title_display = ui.label("").classes("text-secondary")

            camera_description = ui.input(
                label="Camera description",
                placeholder=f"Enter any value... [{DESCRIPTION_LIMIT}]",
                on_change=lambda e: camera_description_display.set_text(
                    f"[{len(camera_description.value)}/{DESCRIPTION_LIMIT}] {camera_description.value}"
                ),
                validation={
                    "Description is too long": lambda value: len(value)
                    <= DESCRIPTION_LIMIT,
                    "Description is too short": lambda value: len(value.strip()) != 0,
                },
            ).classes("w-full")
            camera_description_display = ui.label("").classes("text-secondary")

            camera_ip_address = ui.input(
                label="Camera IPV4 address",
                placeholder=f"000.000.000.000 [{15}]",
                on_change=lambda e: camera_ip_address_display.set_text(
                    f"[{len(camera_ip_address.value)}/15] {camera_ip_address.value}"
                ),
                validation={
                    "IP address is too long": lambda value: len(value) <= 15,
                    "IP address is too short": lambda value: len(value) > 7,
                },
            ).classes("w-full")
            camera_ip_address_display = ui.label("").classes("text-secondary")

            with ui.row().classes("w-full"):
                ui.space()
                ui.button(
                    "Save",
                    on_click=lambda: _handle_create_camera(
                        camera_title,
                        camera_description,
                        camera_ip_address,
                        accessor,
                        generate_camera_list,
                    ),
                )

        with ui.column():
            im = "/home/egor/Downloads/drawcore_ocr_damaged.bmp"
            im = Image.open(im)

            # TODO: provide image navigation
            with ui.interactive_image(im) as ii:
                ui.button("Take image").classes("absolute bottom-0 right-0 m-2")

    ui.label("Registered cameras")

    camera_list_container = ui.list().classes("w-full").props("dense")

    def generate_camera_list():
        camera_list_container.clear()
        camera_list = CameraController.list()
        if len(camera_list):
            with camera_list_container:
                for camera in camera_list:
                    with ui.item().props("clickable"):
                        with ui.item_section():
                            with ui.row():
                                ui.label(
                                    f"{camera.title} @ {camera.ip_address}. {camera.description[:20]}"
                                )
                                ui.space()
                                ui.button(
                                    "Remove",
                                    color="negative",
                                    on_click=lambda: _handle_delete_camera(
                                        camera, generate_camera_list
                                    ),
                                ).props("size=sm")

    generate_camera_list()
