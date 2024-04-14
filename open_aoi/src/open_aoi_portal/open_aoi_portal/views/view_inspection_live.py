import functools
from typing import Optional

from rclpy.node import Node
from nicegui import ui, app
from fastapi.responses import RedirectResponse

from open_aoi_portal.settings import ACCESS_PAGE, HOME_PAGE
from open_aoi_core.exceptions import AuthException
from open_aoi_core.controllers.inspection_profile import InspectionProfileController
from open_aoi_core.controllers.accessor import AccessorController
from open_aoi_portal.common import inject_header, get_session, to_thread


def get_view(node: Node):
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

        async def _handle_inspection():
            execute_inspection.disable()
            try:
                partial = functools.partial(
                    node.mediator_execute_inspection, inspection_profile.id
                )
                overall_passed, error, error_description = await to_thread(partial)
            except Exception as e:
                ui.notify(str(e), type="warning")
                execute_inspection.enable()
                return

            node.logger.info(
                f"Inspection result: {overall_passed}. {error}: {error_description}"
            )
            execute_inspection.enable()

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
                        execute_inspection = ui.button(
                            "Inspect",
                            on_click=_handle_inspection,
                        ).classes("w-full")

            with ui.column().classes("col-span-2"):
                image_element = ui.interactive_image().classes("w-full")

    return view
