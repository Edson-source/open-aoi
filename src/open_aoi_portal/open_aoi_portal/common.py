import logging
import asyncio
import functools
import concurrent.futures
from typing import Optional, Tuple

from PIL import Image
from nicegui import events, ui, app
from sqlalchemy.orm import Session


from open_aoi_portal.settings import *
from open_aoi_core.utils import scale
from open_aoi_core.models import AccessorModel, engine
from open_aoi_core.controllers.accessor import AccessorController


logger = logging.getLogger("ui.common")


async def to_thread(func, /, *args, **kwargs):
    """Function implements `asyncio.to_thread` function"""

    loop = asyncio.get_running_loop()
    func_call = functools.partial(func, *args, **kwargs)

    with concurrent.futures.ThreadPoolExecutor() as pool:
        return await loop.run_in_executor(pool, func_call)


def get_session() -> Session:
    """Shorthand for DB session generation"""
    return Session(engine)


def get_overlay(cc, log, color: Optional[str] = None):
    """Create overlay to show inspection result (SVG format for nice gui interactive image)"""

    x = cc.stat_left
    y = cc.stat_top
    w = cc.stat_width
    h = cc.stat_height
    if color is None:
        color = "green" if log.passed else "red"
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{color}" fill-opacity="0.4"/>'


def safe_view(view):
    """Handler to prevent unexpected exceptions in views. Should wrap all views"""

    @functools.wraps(view)
    async def wrapper(*args, **kwargs):
        try:
            return await view(*args, **kwargs)
        except Exception as e:
            logger.exception(e)
            ui.notify(
                "Unexpected exception on the page.",
                type="negative",
            )
            return

    return wrapper


def safe_operation(operation):
    """Handler to prevent unexpected exceptions. Should wrap all handlers inside view"""

    @functools.wraps(operation)
    async def wrapper(*args, **kwargs):
        try:
            return await operation(*args, **kwargs)
        except Exception as e:
            logger.exception(e)
            ui.notify(
                "Failed to perform action due to unexpected exception.",
                type="negative",
            )
            return

    return wrapper


def confirm(msg: str, callback: callable):
    """Function open confirmation dialog"""

    with ui.dialog() as dialog, ui.card():
        ui.label(msg)
        with ui.row().classes("w-full justify-end"):
            ui.button("Cancel", on_click=dialog.close, color="white")
            ui.button("Confirm action", on_click=callback, color="primary")

    dialog.open()


# Global injections
@safe_operation
async def inject_header(accessor: AccessorModel):
    """Function injects common header, that should be present on every page"""

    @safe_operation
    async def _handle_logout_request():

        @safe_operation
        async def _logout():
            AccessorController.revoke_session_access(app.storage.user)
            ui.open(ACCESS_PAGE)

        confirm("You are about to logout. Are you sure?", _logout)

    ui.right_drawer().props("bordered")
    with ui.left_drawer(top_corner=False, bottom_corner=True).props("bordered"):
        ui.button("Overview", on_click=lambda: ui.open(HOME_PAGE)).props(
            "flat align=left icon=home"
        ).tailwind.width("full")
        if accessor.role.allow_system_operations:
            ui.button("Devices", on_click=lambda: ui.open(DEVICES_PAGE)).props(
                "flat align=left icon=photo_camera"
            ).tailwind.width("full")
        if accessor.role.allow_system_operations:
            ui.button("Modules", on_click=lambda: ui.open(MODULES_PAGE)).props(
                "flat align=left icon=widgets"
            ).tailwind.width("full")
        if accessor.role.allow_system_operations:
            ui.button(
                "Inspection profiles",
                on_click=lambda: ui.open(INSPECTION_PROFILE_CREATE_PAGE),
            ).props("flat align=left icon=cameraswitch").tailwind.width("full")
        if accessor.role.allow_system_operations:
            ui.button(
                "Inspection templates", on_click=lambda: ui.open(TEMPLATES_PAGE)
            ).props("flat align=left icon=tune").tailwind.width("full")
        if accessor.role.allow_inspection_view:
            ui.button(
                "Inspection (live)",
                on_click=lambda: ui.open(INSPECTION_PAGE),
            ).props("flat align=left icon=online_prediction").tailwind.width("full")
        ui.separator()
        ui.button("Logout", on_click=_handle_logout_request).props(
            "flat color=negative align=left icon=logout"
        ).tailwind.width("full")
    with ui.header(fixed=True).classes("py-1 items-center"):
        ui.markdown(f"**{APP_TITLE}** | Powered by ROS")


@safe_operation
async def inject_text_field(
    label: str,
    placeholder: str,
    limit: int,
    validation: Optional[dict] = dict(),
):
    """Inject text field with dynamic value display. Default validations check text length."""
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


@safe_operation
async def inject_numeric_field(
    label: str,
    step: int = 1,
    precision: int = 0,
    validation: Optional[dict] = dict(),
):
    """Inject numeric field"""
    field = ui.number(
        label=label, validation=validation, step=step, precision=precision
    ).classes("w-full")
    return field


class InspectionZoneManager:
    # Image navigation system (viewport is imaginary square that crops visible part of image)
    _viewport_offset: Tuple[int, int] = [0, 0]  # (Xpx, Ypx), change to move view port
    _viewport_size: Tuple[int, int] = [0, 0]  # (Xpx, Ypx), change to zoom

    # Points (always 2 points - define square, which is basically an inspection zone)
    # Coordinate system starts in left upper corner
    # Local p1, p2 - coordinates [x, y] inside image canvas (no zoom, offset applied)
    _local_p1: Optional[Tuple[float, float]] = None
    _local_p2: Optional[Tuple[float, float]] = None

    # Global coordinates for real size image (local -> apply zoom, offset -> global)
    _global_p1: Optional[Tuple[int, int]] = None
    _global_p2: Optional[Tuple[int, int]] = None

    def __init__(
        self,
        image: Image,
        viewport_size_limits: Tuple[int, int],  # min, max width
        step=50,  # Step for movements of view port along image axis
    ):
        self._im = image

        self._viewport_size_limits = viewport_size_limits
        self._viewport_size = [
            viewport_size_limits[1],  # Max width
            int(
                image.size[1] * viewport_size_limits[1] / image.size[0]
            ),  # Max height (keep ratio of  image)
        ]
        self.step = step

    @safe_operation
    async def inject_editor(self):
        """Create editor with all required elements"""

        with ui.interactive_image(
            self._viewport[0],
            on_mouse=self._mouse_handler,
            events=["mouseup"],
        ) as ii:
            self.ii = ii
            with ui.column().classes("absolute bottom-0 left-0 m-2"):
                # Move viewport
                ui.button(
                    icon="arrow_drop_up",
                    color="white",
                    on_click=lambda: self._move_viewport(-self.step, 1),
                ).props("size=small rounded").classes("w-full")
                with ui.row():
                    ui.button(
                        icon="arrow_left",
                        color="white",
                        on_click=lambda: self._move_viewport(-self.step, 0),
                    ).props("size=small round")
                    ui.button(
                        icon="arrow_right",
                        color="white",
                        on_click=lambda: self._move_viewport(self.step, 0),
                    ).props("size=small round")
                ui.button(
                    icon="arrow_drop_down",
                    color="white",
                    on_click=lambda: self._move_viewport(self.step, 1),
                ).props("size=small rounded").classes("w-full")
                # Zoom
                with ui.row():
                    ui.button(
                        icon="zoom_in",
                        color="white",
                        on_click=lambda: self._zoom(0.9),
                    ).props("size=small round")
                    ui.button(
                        icon="zoom_out",
                        color="white",
                        on_click=lambda: self._zoom(1.1),
                    ).props("size=small round")

    def _inspection_zone_coordinates(self, p1, p2):
        """Convert points to connected component coordinates. If any point is None, return None"""
        if p1 is None or p2 is None:
            return None

        p1_x = p1[0]
        p1_y = p1[1]
        p2_x = p2[0]
        p2_y = p2[1]

        return [  # Convert to CV coordinates
            min([p1_x, p2_x]),
            min([p1_y, p2_y]),
            max([p1_x, p2_x]) - min([p1_x, p2_x]),
            max([p1_y, p2_y]) - min([p1_y, p2_y]),
        ]

    def inspection_zone_connected_component(self):
        """Return inspection zone coordinates as connected component in global (real image) space"""
        return self._inspection_zone_coordinates(self._global_p1, self._global_p2)

    def _move_viewport(self, by: int, axis: int):
        """Apply step to move view port along image"""

        self._clear_points()
        tmp = self._viewport_offset[axis] + by
        if tmp + self._viewport_size[axis] > self._im.size[axis]:
            tmp = self._im.size[axis] - self._viewport_size[axis]
        if tmp < 0:
            tmp = 0

        self._viewport_offset[axis] = tmp
        self.ii.set_source(self._viewport[0])

    def _zoom(self, scale: float):
        """Apply zoom operation"""

        self._clear_points()
        tmp = self._viewport_size
        ratio = tmp[1] / tmp[0]

        tmp[0] = tmp[0] * scale
        if tmp[0] < self._viewport_size_limits[0]:
            tmp[0] = self._viewport_size_limits[0]
        if tmp[0] > self._viewport_size_limits[1]:
            tmp[0] = self._viewport_size_limits[1]
        tmp[1] = tmp[0] * ratio

        self._viewport_size = tmp
        self.ii.set_source(self._viewport[0])

    def _get_marker(self, x, y):
        """Return SVG marker to mark point in template image"""
        return f'<circle cx="{x}" cy="{y}" r="2" fill="yellow" />'

    def _get_zone(self, x, y, w, h):
        """Return SVG square to mark whole zone in template image"""
        return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="yellow" fill-opacity="0.4"/>'

    def _local_to_global(self, x: float, y: float) -> Tuple[int, int]:
        """Convert local coordinated back to global with attention to zoom and offsets"""
        frame, before_rescale_size = self._viewport
        gx = int(
            self._viewport_offset[0] + (x * before_rescale_size[0] / frame.size[0])
        )
        gy = int(
            self._viewport_offset[1] + (y * before_rescale_size[1] / frame.size[1])
        )
        return gx, gy

    def _clear_points(self):
        """Clear all points to safely redefine them. Clear SVG overlay as well"""

        self.ii.content = ""
        self._local_p1 = self._global_p1 = None
        self._local_p2 = self._global_p2 = None

    def _mouse_handler(self, e: events.MouseEventArguments):
        """
        Handles mouse clicks inside main editor frame. 1st and 2nd clicks define 1st and 2nd point of
        inspection zone, 3rd click discard changes.
        """
        content = ""
        # Third click -> clean points
        if self._local_p1 is not None and self._local_p2 is not None:
            self._clear_points()
            return
        # First click -> first point
        if self._local_p1 is None:
            self._local_p1 = [e.image_x, e.image_y]
            content += self._get_marker(e.image_x, e.image_y)

            self.ii.content = content
            return

        if self._local_p2 is None:
            assert self._local_p1 is not None
            self._local_p2 = [e.image_x, e.image_y]
            content += self._get_marker(e.image_x, e.image_y)
            content += self._get_marker(self._local_p1[0], self._local_p1[1])

            zone = self._get_zone(
                *self._inspection_zone_coordinates(self._local_p1, self._local_p2)
            )
            content += zone

            self._global_p1 = self._local_to_global(
                self._local_p1[0], self._local_p1[1]
            )
            self._global_p2 = self._local_to_global(
                self._local_p2[0], self._local_p2[1]
            )

            self.ii.content = content
            return

    @property
    def _viewport(self) -> Image:
        """Return modified image after zoom and offset"""
        im = self._im

        off_x, off_y = self._viewport_offset
        x, y = self._viewport_size

        im = im.crop((off_x, off_y, off_x + x, off_y + y))
        before_rescale_size = im.size
        im = scale(im, 1000)
        return im, before_rescale_size
