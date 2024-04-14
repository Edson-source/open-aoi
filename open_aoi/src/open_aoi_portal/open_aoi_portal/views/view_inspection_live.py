import logging
from typing import Optional
import asyncio

from rclpy.node import Node
from nicegui import ui, app
from fastapi.responses import RedirectResponse

from open_aoi_portal.settings import ACCESS_PAGE, HOME_PAGE
from open_aoi_core.constants import ImageAcquisitionConstants
from open_aoi_core.exceptions import AuthException, ROSServiceError
from open_aoi_core.controllers.inspection_profile import InspectionProfileController
from open_aoi_core.controllers.accessor import AccessorController
from open_aoi_portal.common import inject_header, get_session, to_thread

logger = logging.getLogger("ui.inspection_live")


def get_view(node: Node):
    def _capture_image(ip_address: str):
        return node.image_acquisition_capture_image(
            camera_ip_address=ip_address,
            camera_emulation_mode=True,
        )

    async def view(profile_id: int) -> Optional[RedirectResponse]:
        session = get_session()
        access_controller = AccessorController(session)
        inspection_profile_controller = InspectionProfileController(session)

        try:
            accessor = access_controller.identify_session_accessor(app.storage.user)
        except AuthException:
            return RedirectResponse(ACCESS_PAGE)

        # ------------------------------------
        # Handlers

        async def _handle_capture_image():
            try:
                im, error, error_description = await to_thread(
                    _capture_image, inspection_profile.camera.ip_address
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
            image_element.set_source(im)
            capture_image.enable()

        # ------------------------------------

        try:
            inspection_profile = inspection_profile_controller.retrieve(profile_id)
        except Exception as e:
            return RedirectResponse(HOME_PAGE)

        inject_header()

        with ui.grid(columns=3).classes("w-full"):
            with ui.column().classes("col-span-1"):
                ui.markdown(f"#### **Live: {inspection_profile.title}**")
                ui.markdown(
                    f"**Camera**: {inspection_profile.camera.title}.\n\n**Template**: {inspection_profile.template.title}"
                )

                with ui.column().classes("w-full"):
                    with ui.row().classes("w-full"):
                        capture_image = ui.button(
                            "Inspect",
                            on_click=_handle_capture_image,
                        ).classes("w-full")

            with ui.column().classes("col-span-2"):
                image_element = ui.interactive_image().classes("w-full")

    return view
