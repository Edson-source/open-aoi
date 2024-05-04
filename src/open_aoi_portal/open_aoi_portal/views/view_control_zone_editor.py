# TODO: fix left lower to right upper
import logging
from typing import Optional, Tuple

from rclpy.node import Node
from nicegui import events, ui, app
from fastapi.responses import RedirectResponse

from open_aoi_core.utils import crop_stat_image
from open_aoi_core.models import TITLE_LIMIT
from open_aoi_core.exceptions import AuthenticationException
from open_aoi_core.controllers.accessor import AccessorController
from open_aoi_core.controllers.template import TemplateController
from open_aoi_core.controllers.connected_component import ConnectedComponentController
from open_aoi_core.controllers.control_zone import ControlZoneController
from open_aoi_core.controllers.control_handler import ControlHandlerController
from open_aoi_core.controllers.control_target import ControlTargetController
from open_aoi_portal.common import (
    ACCESS_PAGE,
    inject_header,
    inject_text_field,
    get_session,
    confirm,
    scale,
)

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

    async def create_ui(self):
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

    def control_zone(self):
        if self._global_p1 is None or self._global_p2 is None:
            return None

        left_upper = (
            self._global_p1
            if self._global_p1[0] < self._global_p2[0]
            and self._global_p1[1] < self._global_p2[1]
            else self._global_p2
        )
        right_lower = (
            self._global_p1
            if self._global_p1[0] >= self._global_p2[0]
            and self._global_p1[1] >= self._global_p2[1]
            else self._global_p2
        )

        return [  # Convert to CV coordinates
            left_upper[0],
            left_upper[1],
            right_lower[0] - left_upper[0],
            right_lower[1] - left_upper[1],
        ]

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
    async def view(template_id: int) -> Optional[RedirectResponse]:
        session = get_session()
        access_controller = AccessorController(session)
        template_controller = TemplateController(session)
        control_zone_controller = ControlZoneController(session)
        connected_component_controller = ConnectedComponentController(session)
        control_handler_controller = ControlHandlerController(session)
        control_target_controller = ControlTargetController(session)

        try:
            accessor = access_controller.identify_session_accessor(app.storage.user)
        except AuthenticationException:
            return RedirectResponse(ACCESS_PAGE)

        inject_header()

        # -----------------------------------
        # Handlers
        def _handle_control_zone_create():
            cc = manager.control_zone()
            logger.info(str(cc))
            try:
                assert control_zone_title.validate()
                assert control_handler_selection.validate()
                assert cc is not None
            except AssertionError:
                ui.notify(
                    "Control zone require a title. control handler and selected zone in the template image.",
                    type="negative",
                )
                return

            try:
                control_handler = control_handler_controller.retrieve(
                    control_handler_selection.value
                )
                control_zone = control_zone_controller.create(
                    control_zone_title.value.strip(), template, accessor
                )
                connected_component = connected_component_controller.create(
                    cc[0], cc[1], cc[2], cc[3], control_zone
                )
                control_target = control_target_controller.create(
                    control_handler, control_zone
                )
                control_zone_controller.commit()
            except Exception as e:
                logger.exception(e)
                ui.notify("Failed to create control zone!", type="negative")
                return

            ui.notify("Control zone created.", type="positive")
            _inject_control_zone_list()

        def _handle_control_zone_delete(control_zone):
            def execute():
                try:
                    for control_target in control_zone.control_target_list:
                        control_target_controller.delete(control_target)
                    connected_component_controller.delete(control_zone.cc)
                    control_zone_controller.delete(control_zone)
                    control_zone_controller.commit()
                except Exception as e:
                    logger.exception(e)
                    ui.notify(
                        "Failed to delete control zone as it is a dependency!",
                        type="negative",
                    )
                    return
                ui.notify("Control zone deleted!", type="positive")
                _inject_control_zone_list()

            confirm("Are you sure?", execute)

        def _handle_control_zone_preview(control_zone):
            stat = [
                control_zone.cc.stat_left,
                control_zone.cc.stat_top,
                control_zone.cc.stat_width,
                control_zone.cc.stat_height,
            ]
            cropped = crop_stat_image(im, stat)
            with ui.dialog() as dialog, ui.card():
                ui.interactive_image(cropped)
                with ui.row().classes("w-full justify-end"):
                    ui.button("Close", on_click=dialog.close, color="white")

            dialog.open()

        # Local injections
        def _inject_control_zone_list():
            control_zone_container.clear()

            try:
                # TODO: filter with where
                control_zone_list = [
                    cz
                    for cz in control_zone_controller.list()
                    if cz.template_id == template.id
                ]
            except:
                ui.notify("Failed to list control zones!", type="negative")
                return

            if len(control_zone_list):
                with control_zone_container:
                    for control_zone in control_zone_list:
                        with ui.item().classes("w-full").props("clickable"):
                            with ui.item_section():
                                with ui.row():
                                    ui.label(f"{control_zone.title}")
                                    ui.space()
                                    ui.button(
                                        icon="preview",
                                        on_click=(
                                            lambda cz: lambda: _handle_control_zone_preview(
                                                cz
                                            )
                                        )(control_zone),
                                    ).props("size=sm")
                                    ui.button(
                                        "Remove",
                                        color="negative",
                                        on_click=(
                                            lambda cz: lambda: _handle_control_zone_delete(
                                                cz
                                            )
                                        )(control_zone),
                                    ).props("size=sm")
            else:
                with control_zone_container:
                    with ui.card().classes("w-full bg-primary text-white"):
                        ui.markdown("**No zones to show**")

        # -----------------------------------

        try:
            template = template_controller.retrieve(template_id)
            control_handler_list = control_handler_controller.list()
        except Exception as e:
            logger.exception(e)
            ui.notify("Failed to get data fro database!", type="negative")
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
            with ui.grid(columns=4).classes("justify-left w-full"):
                with ui.column().classes("col-span-3"):
                    await manager.create_ui()
                with ui.list().classes("col-span-1").props(
                    "dense"
                ) as control_zone_container:
                    _inject_control_zone_list()

            control_zone_title = inject_text_field(
                "Title", "Enter short name for this control zone", TITLE_LIMIT
            )
            control_handler_selection = ui.select(
                label="Control handler (module)",
                options=dict([(ch.id, ch.title) for ch in control_handler_list]),
                validation={"Value is required": lambda value: value is not None},
            ).classes("w-full")

            with ui.row().classes("w-full"):
                ui.space()
                ui.button(
                    "Save", on_click=_handle_control_zone_create, color="positive"
                )

    return view
