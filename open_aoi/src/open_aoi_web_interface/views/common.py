from nicegui import ui, app
from nicegui.elements.mixins.validation_element import ValidationElement

from open_aoi.controllers import AccessorController
from open_aoi.models import AccessorModel


colors = dict(primary="#3A6B35", secondary="#CBD18F")

HOME_PAGE = "/"
ACCESS_PAGE = "/access"
INSPECTION_PROFILE_PAGE = "/inspection/profile"
INSPECTION_LIVE_PAGE = "/inspection/live"
DEVICES_PAGE = "/devices"
TEMPLATES_PAGE = "/template"
SETTINGS_PAGE = "/settings"


def _handle_logout_request():
    def logout():
        AccessorModel.revoke_access(app.storage.user)
        ui.open(ACCESS_PAGE)

    with ui.dialog() as dialog, ui.card():
        ui.label("You are about to logout. Are you sure?")
        with ui.row().classes("w-full justify-end"):
            ui.button("Cancel", on_click=dialog.close, color="white")
            ui.button("Confirm", on_click=logout, color="primary")

    dialog.open()


def inject_header():
    ui.right_drawer()
    with ui.left_drawer(top_corner=False, bottom_corner=True).props("bordered"):
        ui.button("Overview", on_click=lambda: ui.open(HOME_PAGE)).props(
            "flat"
        ).tailwind.width("full")
        ui.button("Devices", on_click=lambda: ui.open(DEVICES_PAGE)).props(
            "flat"
        ).tailwind.width("full")
        ui.button("Settings", on_click=lambda: ui.open(SETTINGS_PAGE)).props(
            "flat"
        ).tailwind.width("full")
        ui.button("Inspection", on_click=lambda: ui.open(INSPECTION_LIVE_PAGE)).props(
            "flat"
        ).tailwind.width("full")
        ui.button("Profiles", on_click=lambda: ui.open(INSPECTION_PROFILE_PAGE)).props(
            "flat"
        ).tailwind.width("full")
        ui.button("Templates", on_click=lambda: ui.open(TEMPLATES_PAGE)).props(
            "flat"
        ).tailwind.width("full")
        ui.separator()
        ui.button("Logout", on_click=_handle_logout_request).props(
            "flat color=negative"
        ).tailwind.width("full")
    with ui.header(fixed=True).classes("py-1 items-center"):
        ui.markdown("**AOI Portal** | Powered by ROS")
        ui.badge("offline", color="grey").classes("ml-1").props("rounded")
        # ui.badge("online", color="red").classes("ml-1").props("rounded")


def access_guard() -> AccessorModel:
    accessor_id = AccessorModel.accessor_from_session(app.storage.user)
    accessor = AccessorController.retrieve(accessor_id)
    return accessor
