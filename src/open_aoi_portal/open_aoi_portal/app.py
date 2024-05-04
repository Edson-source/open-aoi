import logging
import threading

import rclpy
from rclpy.executors import ExternalShutdownException
from nicegui import Client, app, ui, ui_run

from open_aoi_portal.settings import *
from open_aoi_core.settings import STORAGE_SECRET
from open_aoi_core.services import StandardService
from open_aoi_portal.views.view_home import get_view as get_view_home
from open_aoi_portal.views.view_access import get_view as get_view_access
from open_aoi_portal.views.view_devices import get_view as get_view_devices
from open_aoi_portal.views.view_modules import get_view as get_view_modules
from open_aoi_portal.views.view_template import get_view as get_view_template
from open_aoi_portal.views.view_inspection_zone_editor import (
    get_view as get_inspection_zone_editor_view,
)
from open_aoi_portal.views.view_inspection_profile import (
    get_view as get_view_inspection_profile,
)
from open_aoi_portal.views.view_inspection import (
    get_view as get_view_inspection,
)

# from views.view_inspection_log import (
#     view as view_inspection_log,
# )


class Service(StandardService):
    NODE_NAME = "open_aoi_portal"

    def __init__(self) -> None:
        super().__init__()

        self.await_dependencies(
            [
                self.image_acquisition_capture_cli,
                self.mediator_execute_inspection_cli,
            ]
        )

        with Client.auto_index_client:
            ui.page(HOME_PAGE, title=f"Home | {APP_TITLE}")(get_view_home(self))
            ui.page(ACCESS_PAGE, title=f"Access | {APP_TITLE}")(get_view_access(self))
            ui.page(DEVICES_PAGE, title=f"Devices | {APP_TITLE}")(
                get_view_devices(self)
            )
            ui.page(MODULES_PAGE, title=f"Modules | {APP_TITLE}")(
                get_view_modules(self)
            )
            ui.page(TEMPLATES_PAGE, title=f"Templates | {APP_TITLE}")(
                get_view_template(self)
            )
            ui.page(
                CONTROL_ZONE_PAGE,
                title=f"Inspection zone editor | {APP_TITLE}",
            )(get_inspection_zone_editor_view(self))
            ui.page(
                INSPECTION_PROFILE_CREATE_PAGE,
                title=f"Inspection profiles | {APP_TITLE}",
            )(get_view_inspection_profile(self))
            ui.page(
                INSPECTION_PROFILE_EDIT_PAGE, title=f"Inspection profiles | {APP_TITLE}"
            )(get_view_inspection_profile(self))
            ui.page(INSPECTION_PAGE, title="Inspection | AOI Portal")(
                get_view_inspection(self)
            )

            # ui.page(
            #     "/profile/{profile_id}/inspection/{inspection_id}",
            #     title="Inspection log | AOI Portal",
            # )(view_inspection_log)


def main() -> None:
    # NOTE: This function is defined as the ROS entry point in setup.py, but it's empty to enable NiceGUI auto-reloading
    pass


def ros_main() -> None:
    rclpy.init()
    node = Service()
    try:
        rclpy.spin(node)
    except ExternalShutdownException:
        pass


app.on_startup(lambda: threading.Thread(target=ros_main).start())
ui_run.APP_IMPORT_STRING = f"{__name__}:app"  # ROS2 uses a non-standard module name, so we need to specify it here
ui.run(
    show=False,
    favicon="🚀",
    title=APP_TITLE,
    storage_secret=STORAGE_SECRET,
    uvicorn_logging_level="info",
    reload=False,  # TODO: fix reloading :(
)
