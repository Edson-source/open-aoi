import logging
from datetime import datetime
from typing import Optional

from nicegui import app, ui
from fastapi.responses import RedirectResponse

from open_aoi_core.services import StandardClient
from open_aoi_core.controllers.accessor import AccessorController
from open_aoi_core.controllers.inspection import InspectionController
from open_aoi_core.exceptions import AuthenticationException
from open_aoi_portal.settings import (
    ACCESS_PAGE,
    INSPECTION_DETAIL_PAGE,
    HOME_PAGE,
    APP_TITLE,
)
from open_aoi_portal.common import (
    inject_header,
    get_session,
    safe_view,
    safe_operation,
)

logger = logging.getLogger("ui.home")

# How many inspections per page to show
SELECT_AMOUNT = 4  # +1


def get_view(node: StandardClient):
    @safe_view
    async def view(
        select_from_id: Optional[int] = None, select_to_id: Optional[int] = None
    ) -> Optional[RedirectResponse]:
        session = get_session()
        accessor_controller = AccessorController(session)
        inspection_controller = InspectionController(session)

        try:
            accessor = accessor_controller.identify_session_accessor(app.storage.user)
            assert accessor.role.allow_system_view
            assert accessor.role.allow_inspection_view
            assert (select_from_id is not None and select_to_id is not None) or (
                select_from_id is None and select_to_id is None
            )
        except (AssertionError, AuthenticationException):
            accessor_controller.revoke_session_access(app.storage.user)
            return RedirectResponse(ACCESS_PAGE)

        # ------------------------------------
        # Local injections
        @safe_operation
        async def _inject_inspection_list():
            nonlocal select_from_id, select_to_id, do_update
            if select_from_id is None and select_to_id is None:
                try:
                    last_inspection = inspection_controller.retrieve_last()
                    assert last_inspection is not None
                except AssertionError:
                    pass
                else:
                    select_from_id = last_inspection.id
                    select_to_id = select_from_id - SELECT_AMOUNT

            try:
                inspection_list = inspection_controller.list(
                    inspection_controller.Order.desc,
                    select_from_id=select_from_id,
                    select_to_id=select_to_id,
                )
                inspection_list_container.clear()
            except Exception as e:
                logger.exception(e)
                ui.notify("Failed to list recent inspections.", type="negative")
                return

            if len(inspection_list):
                with inspection_list_container:
                    for inspection in inspection_list:
                        url = INSPECTION_DETAIL_PAGE.format(inspection_id=inspection.id)
                        with ui.item().props("clickable"):
                            with ui.item_section():
                                with ui.row():
                                    ui.markdown(
                                        (
                                            f"Inspection {inspection.id} on {inspection.inspection_profile.identification_code} at  {inspection.created_at}. "
                                            f"Overall **{ 'passed' if inspection.overall_passed else 'rejected'}** "
                                        )
                                    )
                                    ui.space()
                                    ui.button(
                                        icon="info",
                                        color="white",
                                        on_click=lambda: ui.open(url),
                                    ).props("size=sm")
                next_page_container.clear()
                with next_page_container:
                    ui.space()
                    ui.button(
                        icon="navigate_before",
                        color="white",
                        on_click=lambda: ui.open(
                            f"{HOME_PAGE}?select_from_id={inspection_list[0].id}&select_to_id={inspection_list[0].id + SELECT_AMOUNT}"
                        ),
                    )
                    if (
                        inspection_list[-1].id - 1 > 0
                    ):  # At least one inspection to show
                        ui.button(
                            icon="navigate_next",
                            color="white",
                            on_click=lambda: ui.open(
                                f"{HOME_PAGE}?select_from_id={inspection_list[-1].id}&select_to_id={inspection_list[-1].id - SELECT_AMOUNT}",
                            ),
                        )
            else:
                with inspection_list_container:
                    with ui.card().classes("w-full bg-primary text-white"):
                        ui.markdown("**No recent inspections to show**")

            if do_update:
                last_update.set_content(f"Last update *{datetime.now():%X}*")

        # ------------------------------------

        await inject_header(accessor)
        ui.markdown("#### **Overview**")
        ui.markdown(
            f"Welcome to **{APP_TITLE}**. You are logged in as {accessor.title}. "
        )

        if accessor.role.allow_system_operations:
            with ui.expansion(caption="Short user manual").classes("w-full"):
                with ui.timeline(side="right"):
                    ui.timeline_entry(
                        (
                            "In order to begin create camera device. "
                            "Camera should be connected to hosting computer and have reachable IP address. ",
                        ),
                        title="Camera",
                        subtitle="Step 1.",
                    )
                    ui.timeline_entry(
                        (
                            "Continue with creating template. Templates are golden images of the product you want to inspect. "
                            "Template image will be captured with the camera you created earlier. "
                        ),
                        title="Template",
                        subtitle="Step 2.",
                    )
                    ui.timeline_entry(
                        (
                            "Optionally load custom module to use for inspection. "
                            "Custom modules are python files, that will be invoked to perform inspection. "
                            "If no custom logic is required for your application, skip this step. "
                        ),
                        title="Custom modules (optional)",
                        subtitle="Step 3.",
                    )
                    ui.timeline_entry(
                        (
                            "After template is created, hit edit button to create so called inspection zones. "
                            "Inspection zone is a small rectangular on the image where the defect is expected. "
                            "Select desired inspection handler (module), each module is responsible for single type of defects. "
                        ),
                        title="Inspection zones",
                        subtitle="Step 4.",
                    )
                    ui.timeline_entry(
                        (
                            "The last preparation step is to identify your product and assign it an inspection template. "
                            "This is done with inspection profiles. Create profile for each product and pass barcode of the product for identification. "
                        ),
                        title="Inspection profile",
                        subtitle="Step 5.",
                    )
                    ui.timeline_entry(
                        (
                            "Give it a shot with manual trigger. Go to live inspection and trigger desired camera. "
                            "The image will be captured, product will be identified and the inspection conducted! "
                            "Automatic pin triggers are defined at step 1. and are related to camera."
                        ),
                        title="Test",
                        subtitle="Step 7.",
                        icon="rocket",
                    )

        ui.markdown("##### **Recent inspections**")

        last_update = ui.markdown("not updated")
        inspection_list_container = ui.list().classes("w-full").props("dense")
        next_page_container = ui.row().classes("w-full")

        do_update = select_from_id is None
        if do_update:
            ui.timer(3.0, _inject_inspection_list)
        await _inject_inspection_list()

    return view
