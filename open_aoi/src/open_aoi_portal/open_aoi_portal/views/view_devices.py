import logging
from typing import Optional

from rclpy.node import Node
from nicegui import ui, app
from fastapi.responses import RedirectResponse

from open_aoi_portal.settings import ACCESS_PAGE
from open_aoi_core.constants import ImageAcquisitionConstants
from open_aoi_core.exceptions import AuthException, ROSServiceError
from open_aoi_core.controllers.camera import CameraController
from open_aoi_core.controllers.accessor import AccessorController
from open_aoi_core.models import TITLE_LIMIT, DESCRIPTION_LIMIT, CameraModel
from open_aoi_portal.common import (
    inject_header,
    inject_text_field,
    get_session,
    to_thread,
)

logger = logging.getLogger("ui.devices")


def get_view(node: Node):
    def _heavy_capture_image(ip_address: str):
        return node.image_acquisition_capture_image(
            camera_ip_address=ip_address,
            camera_emulation_mode=True,
        )

    async def view() -> Optional[RedirectResponse]:
        session = get_session()
        access_controller = AccessorController(session)
        camera_controller = CameraController(session)
        try:
            accessor = access_controller.identify_session_accessor(app.storage.user)
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
                camera_controller.create(
                    title=camera_title.value.strip(),
                    description=camera_description.value.strip(),
                    ip_address=camera_ip_address.value.strip(),
                    accessor=accessor,
                )
                camera_controller.commit()
            except Exception as e:
                logger.exception(e)
                ui.notify("Failed to create camera")
                return

            ui.notify(f"Camera {camera_title.value.strip()} created!", type="positive")

            _inject_camera_list()

        def _handle_delete_camera(camera: CameraModel):
            try:
                camera_controller.delete(camera)
                camera_controller.commit()
            except Exception as e:
                logger.exception(e)
                ui.notify("Failed to delete camera!", type="negative")
                return
            ui.notify("Camera was deleted!", type="positive")
            _inject_camera_list()

        async def _handle_capture_image():
            try:
                assert camera_ip_address.validate()
            except AssertionError:
                ui.notify("IP is missing", type="negative")
                return
            capture_image.disable()
            try:
                im, error, error_description = await to_thread(
                    _heavy_capture_image, camera_ip_address.value.strip()
                )
            except ROSServiceError as e:
                ui.notify(str(e), type="warning")
                capture_image.enable()
                return

            if error != ImageAcquisitionConstants.Error.NONE:
                ui.notify(error_description, type="negative")
                capture_image.enable()
                return

            if im is None:
                ui.notify("Failed to capture image", type="warning")
                return

            # Reduce size to speed up network image transfer
            image_dialog.open()
            image_element.set_source(im)

            capture_image.enable()

        # Local injections
        def _inject_camera_list():
            camera_list_container.clear()

            try:
                camera_list = camera_controller.list()
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
                                            lambda c: (lambda: _handle_delete_camera(c))
                                        )(camera),
                                    ).props("size=sm")
            else:
                with camera_list_container:
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
                    "Value is too short": lambda value: len(value) >= 7,
                },
            )
            camera_ip_address.set_value("000.000.000.000")

            with ui.row().classes("w-full"):
                ui.space()
                capture_image = ui.button(
                    "Capture image", on_click=_handle_capture_image, icon="photo_camera"
                )
                ui.button("Save", on_click=_handle_create_camera)

        with ui.dialog() as image_dialog, ui.card():
            image_element = ui.interactive_image()
            with ui.row().classes("w-full justify-end"):
                ui.button("Close", on_click=image_dialog.close, color="white")

        ui.markdown("##### **Registered devices**")

        camera_list_container = ui.list().classes("w-full").props("dense")
        _inject_camera_list()

    return view
