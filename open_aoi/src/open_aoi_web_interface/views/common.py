from nicegui import ui, app

from open_aoi.controllers.accessor import AccessorController
from open_aoi.models import AccessorModel
from open_aoi_web_interface.settings import *


colors = dict(primary="#3A6B35", secondary="#CBD18F")


def _handle_logout_request():
    def logout():
        AccessorController.revoke_session_access(app.storage.user)
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
            "flat align=left icon=home"
        ).tailwind.width("full")
        ui.button("Devices", on_click=lambda: ui.open(DEVICES_PAGE)).props(
            "flat align=left icon=photo_camera"
        ).tailwind.width("full")
        ui.button("Modules", on_click=lambda: ui.open(MODULES_PAGE)).props(
            "flat align=left icon=widgets"
        ).tailwind.width("full")
        ui.button("Inspect", on_click=lambda: ui.open(INSPECTION_PAGE)).props(
            "flat align=left icon=compare"
        ).tailwind.width("full")
        ui.button(
            "Inspection profiles", on_click=lambda: ui.open(INSPECTION_PROFILE_PAGE)
        ).props("flat align=left icon=cameraswitch").tailwind.width("full")
        ui.button(
            "Inspection templates", on_click=lambda: ui.open(TEMPLATES_PAGE)
        ).props("flat align=left icon=tune").tailwind.width("full")
        ui.separator()
        ui.button("Logout", on_click=_handle_logout_request).props(
            "flat color=negative align=left icon=logout"
        ).tailwind.width("full")
    with ui.header(fixed=True).classes("py-1 items-center"):
        ui.markdown("**AOI Portal** | Powered by ROS")
        ui.badge("offline", color="grey").classes("ml-1").props("rounded")
        # ui.badge("online", color="red").classes("ml-1").props("rounded")


def access_guard() -> AccessorModel:
    return AccessorController.identify_session_accessor(app.storage.user)
