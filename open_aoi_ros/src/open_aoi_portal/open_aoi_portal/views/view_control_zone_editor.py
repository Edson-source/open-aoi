import logging
from typing import Optional, Tuple

from rclpy.node import Node
from nicegui import events, ui, app
from fastapi.responses import RedirectResponse

from open_aoi.exceptions import AuthException
from open_aoi.controllers.accessor import AccessorController
from open_aoi.controllers.template import TemplateController
from open_aoi_portal.views.common import ACCESS_PAGE, inject_header, get_session, scale

from PIL import Image

logger = logging.getLogger("ui.control_zone_editor")


class Manager:
    # Image coordinate system
    _viewport_offset: Tuple[int, int] = [0, 0]  # (Xpx, Ypx), change to move view port
    _viewport_size: Tuple[int, int] = [0, 0]  # (Xpx, Ypx), change to zoom

    # Points
    # Local p1, p2 - coordinates [x, y] inside image canvas (no zoom, offset applied)
    _local_p1: Optional[Tuple[float, float]] = None
    _local_p2: Optional[Tuple[float, float]] = None

    # Global coordinates for real size image (local -> apply zoom, offset -> global)
    _global_p1: Optional[Tuple[int, int]] = None
    _global_p2: Optional[Tuple[int, int]] = None

    def __init__(
        self,
        im: Image,
        viewport_size_limits: Tuple[int, int],  # min, max width
        step=50,
    ) -> None:
        self._im = im

        self._viewport_size_limits = viewport_size_limits
        self._viewport_size = [
            viewport_size_limits[1],
            int(im.size[1] * viewport_size_limits[1] / im.size[0]),
        ]
        self.step = step

    def create_ui(self):
        with ui.interactive_image(
            self._frame[0],
            on_mouse=self._mouse_handler,
            events=["mouseup"],
        ) as ii:
            self.ii = ii
            with ui.column().classes("absolute bottom-0 left-0 m-2"):
                # Move viewport
                ui.button(
                    icon="arrow_drop_up",
                    on_click=lambda: self._move_viewport(-self.step, 1),
                ).props("size=small rounded").classes("w-full")
                with ui.row():
                    ui.button(
                        icon="arrow_left",
                        on_click=lambda: self._move_viewport(-self.step, 0),
                    ).props("size=small round")
                    ui.button(
                        icon="arrow_right",
                        on_click=lambda: self._move_viewport(self.step, 0),
                    ).props("size=small round")
                ui.button(
                    icon="arrow_drop_down",
                    on_click=lambda: self._move_viewport(self.step, 1),
                ).props("size=small rounded").classes("w-full")
                # Zoom
                with ui.row():
                    ui.button(
                        icon="zoom_in",
                        on_click=lambda: self._zoom(0.9),
                    ).props("size=small round")
                    ui.button(
                        icon="zoom_out",
                        on_click=lambda: self._zoom(1.1),
                    ).props("size=small round")

    def _move_viewport(self, by: int, axis: int):
        self._clear_points()
        tmp = self._viewport_offset[axis] + by
        if tmp + self._viewport_size[axis] > self._im.size[axis]:
            tmp = self._im.size[axis] - self._viewport_size[axis]
        if tmp < 0:
            tmp = 0
        self._viewport_offset[axis] = tmp
        self.ii.set_source(self._frame[0])

    def _zoom(self, scale: float):
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
        self.ii.set_source(self._frame[0])

    def _get_marker(self, x, y):
        return f'<circle cx="{x}" cy="{y}" r="2" fill="yellow" />'

    def _get_zone(self, x, y, w, h):
        return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="yellow" fill-opacity="0.5"/>'

    def _local_to_global(self, x: float, y: float) -> Tuple[int, int]:
        frame, before_rescale_size = self._frame
        gx = int(
            self._viewport_offset[0] + (x * before_rescale_size[0] / frame.size[0])
        )
        gy = int(
            self._viewport_offset[1] + (y * before_rescale_size[1] / frame.size[1])
        )
        return gx, gy

    def _clear_points(self):
        self.ii.content = ""
        self._local_p1 = self._global_p1 = None
        self._local_p2 = self._global_p2 = None

    def _mouse_handler(self, e: events.MouseEventArguments):
        # self.ii.content = ""
        content = ""
        # Third click -> clean points
        if self._local_p1 is not None and self._local_p2 is not None:
            logger.info("Clear content")
            self._clear_points()
            return
        # First click -> first point
        if self._local_p1 is None:
            logger.info(f"Set p1: x: {e.image_x}, y: {e.image_y}")
            self._local_p1 = [e.image_x, e.image_y]
            content += self._get_marker(e.image_x, e.image_y)

            self.ii.content = content
            return

        if self._local_p2 is None:
            logger.info(f"Set p2: x: {e.image_x}, y: {e.image_y}")
            assert self._local_p1 is not None
            self._local_p2 = [e.image_x, e.image_y]
            content += self._get_marker(e.image_x, e.image_y)
            content += self._get_marker(self._local_p1[0], self._local_p1[1])

            left_upper = (
                self._local_p1
                if self._local_p1[0] < self._local_p2[0]
                and self._local_p1[1] < self._local_p2[1]
                else self._local_p2
            )
            right_lower = (
                self._local_p1
                if self._local_p1[0] >= self._local_p2[0]
                and self._local_p1[1] >= self._local_p2[1]
                else self._local_p2
            )
            zone = self._get_zone(
                left_upper[0],
                left_upper[1],
                right_lower[0] - left_upper[0],
                right_lower[1] - left_upper[1],
            )
            content += zone

            self._global_p1 = self._local_to_global(
                self._local_p1[0], self._local_p1[1]
            )
            self._global_p2 = self._local_to_global(
                self._local_p2[0], self._local_p2[1]
            )
            logger.info(f"Global p1: {self._global_p1}")
            logger.info(f"Global p2: {self._global_p2}")

            self.ii.content = content
            return

    @property
    def _frame(self) -> Image:
        im = self._im

        off_x, off_y = self._viewport_offset
        x, y = self._viewport_size

        im = im.crop((off_x, off_y, off_x + x, off_y + y))
        before_rescale_size = im.size
        im = scale(im, 1000)
        return im, before_rescale_size


def get_view(node: Node):
    def view(template_id: int) -> Optional[RedirectResponse]:
        session = get_session()
        access_controller = AccessorController(session)
        template_controller = TemplateController(session)
        try:
            access_controller.identify_session_accessor(app.storage.user)
        except AuthException:
            return RedirectResponse(ACCESS_PAGE)

        inject_header()

        try:
            template = template_controller.retrieve(template_id)
        except Exception as e:
            logger.exception(e)
            ui.notify("Failed to get template!", type="negative")
            return

        with ui.column().classes("w-full"):
            ui.markdown("### **Control zone editor**")
            ui.markdown(f"#### **Template: {template.title}**")
            ui.markdown(
                (
                    "Define control zone and select related module (control handler) to be applied on defined zone. "
                    "Each module may define it's own requirements for control zone, other wise module is not guaranteed to function correctly."
                )
            )

            try:
                im = template.materialize_image()
            except Exception as e:
                logger.exception(e)
                ui.notify("Failed to get image!", type="negative")
                return

            manager = Manager(im, [100, im.size[0]])
            with ui.row().classes("justify-center w-full"):
                manager.create_ui()

    return view
