import logging
from typing import Optional
from nicegui import ui, app
from fastapi.responses import RedirectResponse

from open_aoi.controllers.accessor import AccessorController
from open_aoi.exceptions import AuthException
from open_aoi_portal.views.common import HOME_PAGE

logger = logging.getLogger("ui.access")


def _handle_access_request(username_input: ui.input, password_input: ui.input):
    accessor = AccessorController.retrieve_by_username(username_input.value)
    try:
        accessor.test_credentials(password=password_input.value)
    except AuthException:
        logger.info("Failed to test credentials")
        ui.notify("Invalid credentials", type="negative")
    else:
        # Allow access
        accessor.grant_session_access(app.storage.user)
        ui.open(HOME_PAGE)


async def view() -> Optional[RedirectResponse]:
    # Render page
    with ui.card().classes("absolute-center w-80"):
        with ui.row().classes("w-full justify-between items-center"):
            ui.markdown("**Enter credentials**")
            info = ui.button(icon="question_mark").props("flat round size=xs")
            info.tooltip("To access system please enter your credentials")
        username_input = ui.input(placeholder="Username").classes("w-full")
        password_input = ui.input(placeholder="Password", password=True).classes(
            "w-full"
        )
        ui.button(
            "Continue",
            color="primary",
            on_click=lambda: _handle_access_request(username_input, password_input),
        ).classes("w-full")

    with ui.header(fixed=True).classes("py-1"):
        ui.markdown("**AOI Portal** | Powered by ROS")
    with ui.footer(fixed=True).classes("py-2"):
        ui.label("Created with Love")
