"""
    This view is used for manual inspection control. Inspection is related to camera and inspection profile. User is suppose to 
    select camera and trigger inspection. This will invoke mediator inspection service, acquire image from selected camera, 
    materialize related template and so on...
"""

import logging
import functools
from typing import Optional, List

from PIL import Image
from nicegui import ui, app
from fastapi.responses import RedirectResponse

from open_aoi_interfaces.msg import InspectionLog
from open_aoi_core.exceptions import AuthenticationException, SystemServiceException
from open_aoi_core.controllers.camera import CameraController
from open_aoi_core.controllers.accessor import AccessorController
from open_aoi_core.controllers.inspection_target import InspectionTargetController
from open_aoi_core.models import InspectionTargetModel
from open_aoi_core.constants import MediatorServiceConstants
from open_aoi_core.services import StandardClient
from open_aoi_core.utils_ros import msg_to_image
from open_aoi_portal.settings import ACCESS_PAGE, HOME_PAGE
from open_aoi_portal.common import (
    inject_header,
    get_session,
    get_overlay,
    to_thread,
    safe_view,
    safe_operation,
)

logger = logging.getLogger("ui.inspection_profile")


def get_view(node: StandardClient):
    @safe_view
    async def view() -> Optional[RedirectResponse]:
        session = get_session()

        accessor_controller = AccessorController(session)
        camera_controller = CameraController(session)
        inspection_target_controller = InspectionTargetController(session)

        try:
            accessor = accessor_controller.identify_session_accessor(app.storage.user)
            assert accessor.role.allow_system_view
            assert accessor.role.allow_inspection_control
        except AuthenticationException:
            return RedirectResponse(ACCESS_PAGE)
        except AssertionError:
            return RedirectResponse(HOME_PAGE)

        # ------------------------------------
        # Handlers

        @safe_operation
        async def _handle_inspection():
            """Handles inspection request"""
            inspection_button.disable()

            # Validate inputs
            try:
                assert camera_selection.validate()
            except AssertionError:
                ui.notify("Camera is required.", type="warning")
                inspection_button.enable()
                return

            # Trigger and await inspection (use threads to not block UI event loops)
            try:
                # Bon Voyage!
                response = await to_thread(
                    functools.partial(
                        node.await_future,
                        node.mediator_inspection(camera_selection.value),
                    )
                )
            except SystemServiceException as e:
                ui.notify(str(e), type="warning")
                inspection_button.enable()
                return

            # Check inspection status
            if response.error != MediatorServiceConstants.Error.NONE:
                ui.notify(
                    f"Inspection failed [{response.error}]: {response.error_description}",
                    type="negative",
                )
                inspection_button.enable()
                return
            else:
                ui.notify(
                    f"Inspection succeeded with overall result: {response.overall_passed}",
                    type="info",
                )

            # Reconstruct image (already saved as blob, so just display)
            image = Image.fromarray(msg_to_image(response.image))
            image_element.set_source(image)

            # Create overlay to show inspection result
            overlay = ""
            for log, target in zip(
                response.inspection_log_list, response.inspection_target_list
            ):
                overlay += get_overlay(target, log)
            image_element.content = overlay

            await _inject_inspection_log(response.inspection_log_list)

            inspection_button.enable()

        # Local injections
        @safe_operation
        async def _inject_inspection_log(
            inspection_log_msg_list: List[InspectionLog],
        ):
            """Function generate inspection log representation"""

            # Clear old records
            inspection_log_container.clear()

            if len(inspection_log_msg_list):
                with inspection_log_container:
                    for log_msg in inspection_log_msg_list:
                        # Retrieve database inspection target by log msg id (log message has same id as inspection target
                        # for identification purposes, log database record however has own independent id).
                        target: InspectionTargetModel = (
                            inspection_target_controller.retrieve(log_msg.id)
                        )
                        try:
                            assert target is not None
                        except AssertionError:
                            ui.notify(
                                "Inspection target record not found in database.",
                                type="negative",
                            )
                            inspection_log_container.clear()
                            return

                        with ui.item():
                            with ui.item_section():
                                with ui.row():
                                    ui.markdown(
                                        f"**{target.inspection_zone.title}** | { 'accepted' if log_msg.passed else 'rejected'}. *{log_msg.log}*"
                                    )
            else:
                with inspection_log_container:
                    with ui.card().classes("w-full bg-warning text-white"):
                        ui.markdown("**Inspection log is empty.**")

        # ------------------------------------

        # List cameras
        camera_list = camera_controller.list()

        # Draw UI
        await inject_header(accessor)
        with ui.grid(columns=3).classes("w-full"):
            with ui.column().classes("col-span-1"):
                ui.markdown(f"### **Live inspection**")
                ui.markdown(
                    (
                        "Live inspection allow to manually control inspection process. This is useful for debugging inspection modules for example. "
                        "Select camera and trigger the inspection. Make sure the product is placed under the selected camera and has identification code on it. "
                        "Product will be identified and related inspection profile will be applied. "
                    )
                )

                ui.markdown(f"#### **Setup**")
                camera_selection = ui.select(
                    dict([(camera.id, camera.title) for camera in camera_list]),
                    label="Please, select camera",
                    validation={"Camera is required": lambda value: value is not None},
                ).classes("w-full")

                with ui.column().classes("w-full"):
                    with ui.row().classes("w-full"):
                        inspection_button = ui.button(
                            "Inspect",
                            on_click=_handle_inspection,
                            color="white",
                        ).classes("w-full")

                ui.markdown(f"#### **Results**")
                ui.markdown("Inspection results will be displayed here.")

                inspection_log_container = ui.list().classes("w-full").props("dense")
                # On first visit draw empty message. This will be replaced with real log
                with inspection_log_container:
                    with ui.card().classes("w-full bg-primary text-white"):
                        ui.markdown("**No results to show.**")

            with ui.column().classes("col-span-2"):
                image_element = ui.interactive_image().classes("w-full")

    return view
