"""
    This view is responsible for camera creation. View also provide camera image preview.
"""

import logging
import ipaddress
from typing import Optional
from functools import partial

from nicegui import ui, app
from fastapi.responses import RedirectResponse
from PIL import Image

from open_aoi_portal.settings import ACCESS_PAGE, HOME_PAGE
from open_aoi_core.utils_ros import message_to_image
from open_aoi_core.utils_basic import scale
from open_aoi_core.constants import ImageAcquisitionConstants, SystemLimit
from open_aoi_core.services import StandardClient
from open_aoi_core.exceptions import (
    AuthenticationException,
    SystemServiceException,
    SystemIntegrityException,
)
from open_aoi_core.controllers.camera import CameraController
from open_aoi_core.controllers.accessor import AccessorController
from open_aoi_core.models import CameraModel
from open_aoi_portal.common import (
    inject_header,
    inject_text_field,
    inject_numeric_field,
    get_session,
    to_thread,
    confirm,
    safe_operation,
    safe_view,
)

logger = logging.getLogger("ui.devices")


def get_view(node: StandardClient):

    @safe_view
    async def view() -> Optional[RedirectResponse]:
        session = get_session()

        accessor_controller = AccessorController(session)
        camera_controller = CameraController(session)

        # Assert access and rights
        try:
            accessor = accessor_controller.identify_session_accessor(app.storage.user)
            assert accessor.role.allow_system_view
            assert accessor.role.allow_system_operations
        except AssertionError:
            return RedirectResponse(HOME_PAGE)
        except AuthenticationException:
            return RedirectResponse(ACCESS_PAGE)

        # ------------------------------------
        # Handlers

        @safe_operation
        async def _handle_create_camera():
            """Handles camera creation"""

            # Validate inputs
            try:
                assert camera_title.validate()
                assert camera_description.validate()
                assert camera_ip_address.validate()
                assert camera_io_pin_trigger.validate()
                assert camera_io_pin_accept.validate()
                assert camera_io_pin_reject.validate()
            except AssertionError:
                ui.notify(
                    "Required values are missing or invalid.",
                    type="negative",
                )
                return

            try:
                camera_controller.create(
                    title=camera_title.value.strip(),
                    description=camera_description.value.strip(),
                    ip_address=camera_ip_address.value.strip(),
                    io_pin_trigger=camera_io_pin_trigger.value,
                    io_pin_accept=camera_io_pin_accept.value,
                    io_pin_reject=camera_io_pin_reject.value,
                    accessor=accessor,
                )
                camera_controller.commit()
            except SystemIntegrityException as e:
                logger.exception(e)
                ui.notify(
                    f"Failed to create camera. {str(e)}",
                    type="negative",
                )
                return

            ui.notify(f"Camera {camera_title.value.strip()} created.", type="positive")

            await _inject_camera_list()

        @safe_operation
        async def _handle_delete_camera(camera: CameraModel):
            """Handle camera delete operation"""

            @safe_operation
            async def _delete():
                try:
                    camera_controller.delete(camera)
                    camera_controller.commit()
                except SystemIntegrityException as e:
                    logger.exception(e)
                    ui.notify(f"Failed to delete camera! {str(e)}", type="negative")
                    return

                ui.notify("Camera was deleted.", type="positive")
                await _inject_camera_list()

            confirm(
                f"You are about to delete device {camera.title}. Are you sure?", _delete
            )

        @safe_operation
        async def _handle_capture_image():
            """
            Handle image acquisition. Send direct request to related service to obtain image from camera.
            Image capturing is long operation and may break NiceGUI event loop (timeout), service
            response should be awaited in separate thread.
            """
            try:
                assert camera_ip_address.validate()
            except AssertionError:
                ui.notify("IP is missing", type="negative")
                return

            capture_image.disable()
            try:
                response = await to_thread(
                    node.await_future,
                    node.image_acquisition_capture_image(
                        camera_ip_address=camera_ip_address.value.strip(),
                    ),
                )
            except SystemServiceException as e:
                logger.exception(e)
                ui.notify(str(e), type="warning")
                capture_image.enable()
                return

            if response.error != ImageAcquisitionConstants.Error.NONE:
                ui.notify(response.error_description, type="negative")
                capture_image.enable()
                return

            if response.image is None:
                ui.notify("Failed to capture image.", type="warning")
                return

            image = message_to_image(response.image)
            image = Image.fromarray(image)

            # Reduce size to speed up network image transfer
            image_dialog.open()
            image_element.set_source(scale(image, 600))

            capture_image.enable()

        # Local injections
        @safe_operation
        async def _inject_camera_list():
            camera_list_container.clear()

            try:
                camera_list = camera_controller.list(camera_controller.Order.desc)
            except Exception as e:
                logger.exception(e)
                ui.notify("Failed to list cameras.", type="negative")
                return

            if len(camera_list):
                with camera_list_container:
                    for camera in camera_list:
                        with ui.item().props("clickable"):
                            with ui.item_section():
                                with ui.row():
                                    ui.markdown(
                                        f"**{camera.title}**. IP: {camera.ip_address}. Trigger: {camera.io_pin_trigger or '-'}. Accept pin: {camera.io_pin_accept or '-'}. Reject: {camera.io_pin_reject or '-'}. {camera.description}"
                                    )
                                    ui.space()
                                    ui.button(
                                        "Remove",
                                        color="negative",
                                        on_click=partial(_handle_delete_camera, camera),
                                    ).props("size=sm")
            else:
                with camera_list_container:
                    with ui.card().classes("w-full bg-primary text-white"):
                        ui.markdown("**No cameras to show**")

        # ------------------------------------

        await inject_header(accessor)

        ui.markdown("#### **Devices**")
        ui.markdown(
            (
                "Create new camera device here to be used for inspection image acquisition. Camera should be connected via Ethernet (should have valid IP address). "
                "If you want to trigger inspection automatically define trigger, accept and reject pins. When trigger pin is set to HIGH, it will trigger the inspection. Otherwise leave pins empty. "
                "To test camera connection use capture image button. "
            )
        )
        with ui.column().classes("w-full"):
            ui.markdown("##### **Create new device**")
            camera_title = await inject_text_field(
                "Camera title", "Enter any value...", SystemLimit.TITLE_LENGTH
            )
            camera_description = await inject_text_field(
                "Camera description",
                "Enter any value...",
                SystemLimit.DESCRIPTION_LENGTH,
            )

            def _is_ip_address(value: str) -> bool:
                try:
                    ipaddress.ip_address(value)
                except ValueError:
                    return False
                return True

            camera_ip_address = await inject_text_field(
                "Camera IPV4 address",
                "0.0.0.0",
                15,
                validation={
                    "Value is too short": lambda value: len(value) >= 7,
                    "Value is not valid IP address": _is_ip_address,
                },
            )
            camera_ip_address.set_value("0.0.0.0")
            camera_io_pin_trigger = await inject_numeric_field(
                "Trigger I/O pin (leave empty to ignore)", step=1, precision=0
            )

            camera_io_pin_accept = await inject_numeric_field(
                "Acceptance I/O pin (should be defined if trigger pin is defined)",
                step=1,
                precision=0,
            )
            camera_io_pin_reject = await inject_numeric_field(
                "Rejection I/O pin (should be defined if trigger pin is defined)",
                step=1,
                precision=0,
            )

            with ui.row().classes("w-full"):
                ui.space()
                capture_image = ui.button(
                    "Capture image",
                    on_click=_handle_capture_image,
                    icon="photo_camera",
                    color="white",
                )
                ui.button("Save", on_click=_handle_create_camera, color="positive")

        with ui.dialog() as image_dialog, ui.card():
            image_element = ui.interactive_image()
            with ui.row().classes("w-full justify-end"):
                ui.button("Close", on_click=image_dialog.close, color="white")

        ui.markdown("##### **Registered devices**")
        ui.markdown(
            "Here is the list of existing devices. Device may be deleted here if no inspections reference this device. "
        )

        camera_list_container = ui.list().classes("w-full").props("dense")
        await _inject_camera_list()

    return view
