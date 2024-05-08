"""
    This page is used to review conducted inspections. View load template image and test image to compare.
    This view is different from others as it does not offer any actions and is just viewer for inspection results (require inspection id).
"""

import logging
from typing import Optional

from nicegui import ui, app
from fastapi.responses import RedirectResponse

from open_aoi_core.services import StandardClient
from open_aoi_core.exceptions import (
    AuthenticationException,
    AssetIntegrityException,
    SystemIntegrityException,
)
from open_aoi_core.controllers.accessor import AccessorController
from open_aoi_core.controllers.inspection import InspectionController
from open_aoi_core.models import (
    InspectionModel,
)
from open_aoi_portal.settings import ACCESS_PAGE, HOME_PAGE
from open_aoi_portal.common import inject_header, get_session, safe_view, get_overlay

logger = logging.getLogger("ui.inspection_detail")


def get_view(node: StandardClient):
    @safe_view
    async def view(inspection_id: int) -> Optional[RedirectResponse]:
        session = get_session()

        accessor_controller = AccessorController(session)
        inspection_controller = InspectionController(session)

        try:
            assert inspection_id is not None
            accessor = accessor_controller.identify_session_accessor(app.storage.user)
            assert accessor.role.allow_system_view
            assert accessor.role.allow_inspection_view
        except AuthenticationException:
            return RedirectResponse(ACCESS_PAGE)
        except AssertionError:
            return RedirectResponse(HOME_PAGE)

        try:
            inspection: InspectionModel = inspection_controller.retrieve(inspection_id)
            assert inspection is not None
        except AssertionError:
            return RedirectResponse(HOME_PAGE)

        try:
            template_image = inspection.inspection_profile.template.materialize_image()
        except (AssetIntegrityException, SystemIntegrityException) as e:
            logger.exception(e)
            ui.notify(f"Failed to load template. {str(e)}", type="negative")
            return

        try:
            test_image = inspection.materialize_image()
        except (AssetIntegrityException, SystemIntegrityException) as e:
            logger.exception(e)
            ui.notify(f"Failed to load test image. {str(e)}", type="negative")
            return

        await inject_header(accessor)
        with ui.grid(columns=3).classes("w-full"):
            with ui.column().classes("col-span-1"):
                ui.markdown(f"### **Inspection overview**")
                ui.markdown(
                    (
                        f"Inspection with id {inspection.id} was conducted on {inspection.created_at} with overall result **{'passed' if inspection.overall_passed else 'rejected'}**.\n\n"
                        f"**{inspection.inspection_profile.title}** inspection profile was used. "
                        f"**{inspection.inspection_profile.template.title}** template was used. "
                        f"Total number of inspected zones is {len(inspection.inspection_log_list)}. "
                    )
                )

                ui.markdown(f"#### **Inspection log**")
                inspection_log_container = ui.list().classes("w-full").props("dense")
                with inspection_log_container:
                    if len(inspection.inspection_log_list):
                        for log in inspection.inspection_log_list:
                            target = log.inspection_target
                            with ui.item():
                                with ui.item_section():
                                    with ui.row():
                                        ui.markdown(
                                            f"**{target.inspection_zone.title}** | { 'accepted' if log.passed else 'rejected'}. *{log.log}*"
                                        )
                    else:
                        with ui.card().classes("w-full bg-warning text-white"):
                            ui.markdown("**Inspection log is empty.**")

            with ui.column().classes("col-span-2"):
                overlay = ""
                for log in inspection.inspection_log_list:
                    overlay += get_overlay(
                        log.inspection_target.inspection_zone.cc, log
                    )

                ui.markdown(f"#### **Test image**")
                image_test_element = ui.interactive_image(test_image).classes("w-full")
                image_test_element.content = overlay

                overlay = ""
                for log in inspection.inspection_log_list:
                    overlay += get_overlay(
                        log.inspection_target.inspection_zone.cc, log, color="yellow"
                    )

                ui.markdown(f"#### **Template image**")
                image_template_element = ui.interactive_image(template_image).classes(
                    "w-full"
                )
                image_template_element.content = overlay

    return view
