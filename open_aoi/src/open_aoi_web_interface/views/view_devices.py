import logging
from typing import Optional

from PIL import Image
from nicegui import ui
from fastapi.responses import RedirectResponse

from open_aoi.exceptions import AuthException
from open_aoi.controllers.camera import CameraController
from open_aoi.exceptions import ROSServiceError
from open_aoi.controllers.ros_services.image_acquisition import (
    ROSImageAcquisitionService,
)
from open_aoi.models import TITLE_LIMIT, DESCRIPTION_LIMIT, CameraModel
from open_aoi_web_interface.settings import ACCESS_PAGE
from open_aoi_web_interface.views.common import (
    inject_header,
    inject_text_field,
    access_guard,
)

logger = logging.getLogger("ui.devices")


def view() -> Optional[RedirectResponse]:
    try:
        accessor = access_guard()
    except AuthException:
        return RedirectResponse(ACCESS_PAGE)

    # ------------------------------------
    # Handlers

    def _handle_create_camera():
        try:
            assert camera_title.validate()
            assert camera_description.validate()
            assert camera_ip_address.validate()
        except AssertionError:
            ui.notify("Required values are missing", type="negative")
            return

        try:
            CameraController.create(
                title=camera_title.value.strip(),
                description=camera_description.value.strip(),
                ip_address=camera_ip_address.value.strip(),
                accessor=accessor,
            )
        except Exception as e:
            logger.exception(e)
            ui.notify("Failed to create camera")
            return

        ui.notify(f"Camera {camera_title.value.strip()} created!", type="positive")

        _inject_camera_list()

    def _handle_delete_camera(camera: CameraModel):
        try:
            CameraController.delete(camera)
        except:
            ui.notify("Failed to delete camera!", type="negative")
            return
        ui.notify("Camera was deleted!", type="positive")
        _inject_camera_list()

    def _handle_capture_image():
        try:
            assert camera_ip_address.validate()
        except AssertionError:
            ui.notify("IP is missing", type="negative")
            return
        capture_image.disable()
        try:
            ros_image_acquisition = ROSImageAcquisitionService(
                camera_ip=camera_ip_address.value.strip(), emulator=True
            )
            im, error, error_description = ros_image_acquisition.capture()
        except ROSServiceError as e:
            ui.notify(str(e), type="warning")
            capture_image.enable()
            return

        # if error != ROSImageAcquisitionService.ERROR_NONE:
        #     ui.notify(error_description, type="negative")
        #     capture_image.enable()
        #     return

        # im = "/home/egor/Downloads/drawcore_ocr_damaged.bmp"
        # im = Image.open(im)
        print(im)
        # test_image.set_source(im)
        capture_image.enable()

    # Local injections
    def _inject_camera_list():
        camera_list_container.clear()

        try:
            camera_list = CameraController.list()
        except:
            ui.notify("Failed to list cameras!", type="negative")
            return

        if len(camera_list):
            with camera_list_container:
                for camera in camera_list:
                    with ui.item().props("clickable"):
                        with ui.item_section():
                            with ui.row():
                                ui.label(
                                    f"{camera.title} ({camera.ip_address}). {camera.description}"
                                )
                                ui.space()
                                ui.button(
                                    "Remove",
                                    color="negative",
                                    on_click=(
                                        lambda c: lambda: _handle_delete_camera(c)
                                    )(camera),
                                ).props("size=sm")
        else:
            with ui.card().classes("w-full bg-primary text-white"):
                ui.markdown("**No cameras to show**")

    # ------------------------------------

    inject_header()

    ui.markdown("#### **Devices**")
    with ui.column().classes("w-full"):
        ui.markdown("##### **Create new device**")

        camera_title = inject_text_field(
            "Camera title", "Enter any value...", TITLE_LIMIT
        )
        camera_description = inject_text_field(
            "Camera description", "Enter any value...", DESCRIPTION_LIMIT
        )
        camera_ip_address = inject_text_field(
            "Camera IPV4 address",
            "000.000.000.000",
            15,
            validation={
                "Value is too short": lambda value: len(value) > 7,
            },
        )

        with ui.row().classes("w-full"):
            ui.space()
            capture_image = ui.button("Capture image", on_click=_handle_capture_image)
            ui.button("Save", on_click=_handle_create_camera)

        test_image = ui.interactive_image()

    ui.markdown("##### **Registered devices**")

    camera_list_container = ui.list().classes("w-full").props("dense")
    _inject_camera_list()
