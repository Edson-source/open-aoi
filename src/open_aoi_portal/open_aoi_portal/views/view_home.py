import logging
from typing import Optional

from nicegui import app, ui
from fastapi.responses import RedirectResponse

from open_aoi_core.services import StandardClient
from open_aoi_core.controllers.accessor import AccessorController
from open_aoi_core.controllers.inspection import InspectionController
from open_aoi_core.exceptions import AuthenticationException
from open_aoi_portal.common import (
    inject_header,
    get_session,
    ACCESS_PAGE,
)

logger = logging.getLogger("ui.home")


def get_view(node: StandardClient):
    def view() -> Optional[RedirectResponse]:
        session = get_session()
        accessor_controller = AccessorController(session)
        inspection_controller = InspectionController(session)

        try:
            accessor = accessor_controller.identify_session_accessor(app.storage.user)
            assert accessor.role.allow_system_view
        except (AssertionError, AuthenticationException):
            accessor_controller.revoke_session_access(app.storage.user)
            return RedirectResponse(ACCESS_PAGE)

        # ------------------------------------
        # Local injections
        def _inject_inspection_list():
            try:
                inspection_list = inspection_controller.list_nested()
                inspection_list_container.clear()
            except:
                ui.notify("Failed to list recent inspections.", type="negative")
                return

            if len(inspection_list):
                with inspection_list_container:
                    for inspection in inspection_list:
                        with ui.item().props("clickable"):
                            with ui.item_section():
                                with ui.row():
                                    ui.label(
                                        f"{inspection.id}. Overall passed: {inspection.overall_passed}. Product: {inspection.inspection_profile.identification_code}. Date of inspection: {inspection.created_at}"
                                    )
            else:
                with inspection_list_container:
                    with ui.card().classes("w-full bg-primary text-white"):
                        ui.markdown("**No recent inspections to show**")

        # ------------------------------------

        inject_header(accessor)
        ui.markdown("#### **Overview**")
        ui.markdown(f"Welcome to Open AOI. You are logged in as {accessor.title}.")
        ui.markdown("##### **Recent inspections**")
        inspection_list_container = ui.list().classes("w-full").props("dense")
        _inject_inspection_list()

    return view
