"""
    The view is used to authenticate user. User is prompted for credentials (username and password) after that
    credentials are tested against database and in case of success access is permitted. After that permission is stored in server 
    session for user to allow seamless access without need of authentication (cookies need to be allowed).
"""

import logging
from typing import Optional


from nicegui import ui, app
from fastapi.responses import RedirectResponse

from open_aoi_core.controllers.accessor import AccessorController
from open_aoi_core.exceptions import AuthenticationException
from open_aoi_core.services import StandardClient
from open_aoi_portal.common import get_session, safe_operation, safe_view
from open_aoi_portal.settings import APP_TITLE, HOME_PAGE

logger = logging.getLogger("ui.access")


def get_view(node: StandardClient):
    @safe_view
    async def view() -> Optional[RedirectResponse]:
        session = get_session()
        accessor_controller = AccessorController(session)

        # ------------------------------------
        # Handlers
        @safe_operation
        async def _handle_access_request():
            """Handles credential test and grant access if test successes"""
            username = username_input.value.strip()
            password = password_input.value

            try:
                accessor = accessor_controller.retrieve_by_username(username)
                assert accessor is not None
                accessor.test_credentials(password=password)
            except (AuthenticationException, AssertionError) as e:
                logger.exception(e)
                logger.info("Failed to test credentials")
                ui.notify("Credentials are invalid.", type="negative")
            else:
                # Allow access
                accessor.grant_session_access(app.storage.user)
                ui.open(HOME_PAGE)

        # ------------------------------------

        with ui.card().classes("absolute-center w-80"):
            with ui.row().classes("w-full justify-between items-center"):
                ui.markdown("**Please, enter credentials**")
                info = ui.button(icon="question_mark", color="white").props(
                    "flat round size=xs"
                )
                info.tooltip(
                    "To access the system please enter your credentials in form of username and password."
                )

            username_input = (
                ui.input(placeholder="Username")
                .on("keydown.enter", _handle_access_request)
                .classes("w-full")
            )
            password_input = (
                ui.input(placeholder="Password", password=True)
                .on("keydown.enter", _handle_access_request)
                .classes("w-full")
            )

            ui.button(
                "Continue",
                color="primary",
                on_click=_handle_access_request,
            ).classes("w-full")

        with ui.header(fixed=True).classes("py-1"):
            ui.markdown(f"**{APP_TITLE}** | Powered by ROS")
        with ui.footer(fixed=True).classes("py-2"):
            ui.label("Created with Love...")

    return view
