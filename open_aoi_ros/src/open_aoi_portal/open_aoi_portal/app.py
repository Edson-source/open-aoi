from dotenv import load_dotenv

assert load_dotenv(".env")

import logging
import threading
from pathlib import Path

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from nicegui import Client, app, ui, ui_run
from open_aoi.settings import STORAGE_SECRET, WEB_INTERFACE_PORT

from open_aoi_portal.settings import *
from open_aoi_portal.views.view_home import view as view_home
from open_aoi_portal.views.view_access import view as view_access
from open_aoi_portal.views.view_devices import view as view_devices
from open_aoi_portal.views.view_modules import view as view_modules

# from views.view_inspection_profile import (
#     view as view_inspection_profile,
# )
# from views.view_template import view as view_template
# from views.view_control_zone_editor import (
#     view as view_control_zone_editor,
# )
# from views.view_inspection_live import (
#     view as view_inspection_live,
# )
# from views.view_inspection_log import (
#     view as view_inspection_log,
# )


class AOIPortalNode(Node):
    def __init__(self) -> None:
        super().__init__("open_aoi_portal")

        with Client.auto_index_client:
            ui.page(HOME_PAGE, title="Home | AOI Portal")(view_home)
            ui.page(ACCESS_PAGE, title="Access | AOI Portal")(view_access)
            ui.page(DEVICES_PAGE, title="Devices | AOI Portal")(view_devices)
            ui.page(
                MODULES_PAGE,
                title="Modules | AOI Portal",
            )(view_modules)
            # ui.page("/template/{template_id}", title="Template | AOI Portal")(view_template)
            # ui.page("/template", title="Template | AOI Portal")(view_template)
            # ui.page("/inspection/profile/{profile_id}", title="Inspection profiles | AOI Portal")(
            #     view_inspection_profile
            # )
            # ui.page("/inspection/profile", title="Inspection profiles | AOI Portal")(
            #     view_inspection_profile
            # )
            # ui.page("/inspection", title="Inspection | AOI Portal")(view_inspection)
            # ui.page(
            #     "/profile/{profile_id}/inspection/{inspection_id}",
            #     title="Inspection log | AOI Portal",
            # )(view_inspection_log)
            # ui.page(
            #     "/template/test/control_zone",
            #     title="Control zone editor | AOI Portal",
            # )(view_control_zone_editor)

            logging.basicConfig(level=logging.INFO)


def main() -> None:
    # NOTE: This function is defined as the ROS entry point in setup.py, but it's empty to enable NiceGUI auto-reloading
    pass


def ros_main() -> None:
    rclpy.init()
    node = AOIPortalNode()
    try:
        rclpy.spin(node)
    except ExternalShutdownException:
        pass


app.on_startup(lambda: threading.Thread(target=ros_main).start())
ui_run.APP_IMPORT_STRING = f"{__name__}:app"  # ROS2 uses a non-standard module name, so we need to specify it here
ui.run(
    port=WEB_INTERFACE_PORT,
    storage_secret=STORAGE_SECRET,
    uvicorn_logging_level="info",
    favicon="🚀",
    title="Open AOI Portal",
    uvicorn_reload_dirs=str(Path(__file__).parent.resolve()),
)
