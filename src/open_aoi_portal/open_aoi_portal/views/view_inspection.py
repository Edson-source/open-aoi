import functools
from typing import Optional

from PIL import Image
from rclpy.node import Node
from nicegui import ui, app
from fastapi.responses import RedirectResponse

from open_aoi_portal.settings import ACCESS_PAGE, HOME_PAGE
from open_aoi_core.exceptions import AuthException
from open_aoi_core.controllers.camera import CameraController
from open_aoi_core.controllers.accessor import AccessorController
from open_aoi_core.constants import MediatorServiceConstants
from open_aoi_portal.common import inject_header, get_session, to_thread, scale


def get_view(node: Node):
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

        async def _handle_inspection():
            execute_inspection.disable()
            try:
                assert camera_selection.validate()
            except AssertionError:
                ui.notify("Camera is required.", type="warning")
                execute_inspection.enable()
                return

            try:
                partial = functools.partial(
                    node.mediator_execute_inspection, camera_selection.value
                )
                (
                    im,
                    overall_passed,
                    control_log_list,
                    control_target_list,
                    error,
                    error_description,
                ) = await to_thread(partial)
            except Exception as e:
                ui.notify(str(e), type="warning")
                execute_inspection.enable()
                return

            if error != MediatorServiceConstants.Error.NONE:
                ui.notify(
                    f"Inspection failed [{error}]: {error_description}", type="negative"
                )
                execute_inspection.enable()
                return
            else:
                ui.notify(f"Inspection succeeded with overall result: {overall_passed}")

            im = Image.fromarray(im)
            im = scale(im, 600)
            image_element.set_source(im)

            execute_inspection.enable()

        # ------------------------------------

        try:
            camera_list = camera_controller.list()
        except Exception as e:
            return RedirectResponse(HOME_PAGE)

        inject_header()

        with ui.grid(columns=3).classes("w-full"):
            with ui.column().classes("col-span-1"):
                ui.markdown(f"#### **Live**")
                camera_selection = ui.select(
                    dict([(c.id, c.title) for c in camera_list]),
                    label="Camera",
                    validation={"Value is required": lambda value: value is not None},
                ).classes("w-full")
                with ui.column().classes("w-full"):
                    with ui.row().classes("w-full"):
                        execute_inspection = ui.button(
                            "Inspect",
                            on_click=_handle_inspection,
                        ).classes("w-full")

            with ui.column().classes("col-span-2"):
                image_element = ui.interactive_image().classes("w-full")

    return view
