import asyncio
import contextvars
import functools
from typing import Optional
from nicegui import ui, app
from sqlalchemy.orm import Session
from PIL import Image

from open_aoi_core.controllers.accessor import AccessorController
from open_aoi_core.models import AccessorModel, engine
from open_aoi_portal.settings import *


async def to_thread(func, /, *args, **kwargs):
    loop = asyncio.get_running_loop()
    ctx = contextvars.copy_context()
    func_call = functools.partial(ctx.run, func, *args, **kwargs)
    return await loop.run_in_executor(None, func_call)


def confirm(msg: str, callback: callable):
    with ui.dialog() as dialog, ui.card():
        ui.label(msg)
        with ui.row().classes("w-full justify-end"):
            ui.button("Cancel", on_click=dialog.close, color="white")
            ui.button("Confirm action", on_click=callback, color="primary")

    dialog.open()


def scale(im: Image, to_width: int):
    width, height = im.size
    ratio = height / width
    width = to_width
    height = int(width * ratio)
    im = im.resize((width, height))
    return im


def _handle_logout_request():
    def logout():
        AccessorController.revoke_session_access(app.storage.user)
        ui.open(ACCESS_PAGE)

    confirm("You are about to logout. Are you sure?", logout)


def inject_header():
    ui.right_drawer().props("bordered")
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


def inject_text_field(
    label: str, placeholder: str, limit: int, validation: Optional[dict] = dict()
):
    field = ui.input(
        label=label,
        placeholder=f"{placeholder} [{limit}]",
        on_change=lambda e: field_display.set_text(
            f"[{len(field.value)}/{limit}] {field.value}"
        ),
        validation={
            "Value is too long": lambda value: len(value) <= limit,
            "Value is too short": lambda value: len(value.strip()) != 0,
            **validation,
        },
    ).classes("w-full")
    field_display = ui.label("").classes("text-secondary")
    return field


def get_session() -> AccessorModel:
    return Session(engine)
