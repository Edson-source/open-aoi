import logging
from typing import Optional, Tuple

from nicegui import events, ui
from fastapi.responses import RedirectResponse

from open_aoi.exceptions import AuthException
from open_aoi_portal.views.common import (
    ACCESS_PAGE,
    inject_header,
    access_guard,
)

from PIL import Image

logger = logging.getLogger("ui.control_zone_editor")


class Manager:
    # Image coordinate system
    _viewport_offset: Tuple[int, int] = [0, 0]  # (Xpx, Ypx), change to move view port
    _viewport_size: Tuple[int, int] = [0, 0]  # (Xpx, Ypx), change to zoom

    def __init__(
        self,
        im: Image,
        frame_size: Tuple[int, int],
        viewport_size_limits: Tuple[Tuple[int, int], Tuple[int, int]],  # min, max
        step=50,
    ) -> None:
        self._im = im

        self._frame_size = frame_size
        self._viewport_size_limits = viewport_size_limits
        self._viewport_size = viewport_size_limits[1]
        self.step = step

    def create_ui(self):
        with ui.interactive_image(
            self.frame,
            on_mouse=self.mouse_handler,
            events=["mousedown", "mouseup"],
        ) as ii:
            self.ii = ii
            with ui.column().classes("absolute bottom-0 left-0 m-2"):
                # Move viewport
                ui.button(
                    icon="arrow_drop_up",
                    on_click=lambda: self.move_viewport(-self.step, 1),
                ).props("size=small rounded").classes("w-full")
                with ui.row():
                    ui.button(
                        icon="arrow_left",
                        on_click=lambda: self.move_viewport(-self.step, 0),
                    ).props("size=small round")
                    ui.button(
                        icon="arrow_right",
                        on_click=lambda: self.move_viewport(self.step, 0),
                    ).props("size=small round")
                ui.button(
                    icon="arrow_drop_down",
                    on_click=lambda: self.move_viewport(self.step, 1),
                ).props("size=small rounded").classes("w-full")
                # Zoom
                with ui.row():
                    ui.button(
                        icon="zoom_in",
                        on_click=lambda: self.zoom(0.9),
                    ).props("size=small round")
                    ui.button(
                        icon="zoom_out",
                        on_click=lambda: self.zoom(1.1),
                    ).props("size=small round")

    def move_viewport(self, by: int, axis: int):
        tmp = self._viewport_offset[axis] + by
        if tmp + self._viewport_size[axis] > self._im.size[axis]:
            tmp = self._im.size[axis] - self._viewport_size[axis]
        if tmp < 0:
            tmp = 0
        self._viewport_offset[axis] = tmp
        self.ii.set_source(self.frame)

    def zoom(self, scale: float):
        tmp = self._viewport_size

        tmp[0] = tmp[0] * scale
        if tmp[0] < self._viewport_size_limits[0][0]:
            tmp[0] = self._viewport_size_limits[0][0]
        if tmp[0] > self._viewport_size_limits[1][0]:
            tmp[0] = self._viewport_size_limits[1][0]

        tmp[1] = tmp[1] * scale
        if tmp[1] < self._viewport_size_limits[0][1]:
            tmp[1] = self._viewport_size_limits[0][1]
        if tmp[1] > self._viewport_size_limits[1][1]:
            tmp[1] = self._viewport_size_limits[1][1]

        self._viewport_size = tmp
        self.ii.set_source(self.frame)

    def mouse_handler(self, e: events.MouseEventArguments):
        color = "SkyBlue"
        self.ii.content += f'<circle cx="{e.image_x}" cy="{e.image_y}" r="15" fill="none" stroke="{color}" stroke-width="4" />'

    @property
    def frame(self) -> Image:
        im = self._im

        off_x, off_y = self._viewport_offset
        x, y = self._viewport_size

        im = im.crop((off_x, off_y, off_x + x, off_y + y))
        im = im.resize(self._frame_size)
        return im


def view() -> Optional[RedirectResponse]:
    try:
        access_guard()
    except AuthException:
        return RedirectResponse(ACCESS_PAGE)

    inject_header()
    ui.label("Control zone editor")

    im = "/home/egor/Downloads/drawcore_ocr_damaged.bmp"
    im = Image.open(im)

    manager = Manager(im, [1000, 600], [[100, 60], [2000, 1200]])
    manager.create_ui()
