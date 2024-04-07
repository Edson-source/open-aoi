from dotenv import load_dotenv

assert load_dotenv(".env")

import logging
import threading
from pathlib import Path

import rclpy
from rclpy.client import Client as ServiceClient
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from nicegui import Client, app, ui, ui_run
from open_aoi.settings import STORAGE_SECRET

from open_aoi_portal.settings import *
from open_aoi_portal.views.view_home import get_view as get_view_home
from open_aoi_portal.views.view_access import get_view as get_view_access
from open_aoi_portal.views.view_devices import get_view as get_view_devices
from open_aoi_portal.views.view_modules import get_view as get_view_modules
from open_aoi_portal.views.view_template import get_view as get_view_template

from open_aoi_portal.clients.image_acquisition import ROSImageAcquisitionClient
from open_aoi_ros_interfaces.srv import ImageAcquisition, ServiceStatus
from rcl_interfaces.srv._set_parameters import SetParameters

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

logging.basicConfig(level=logging.INFO)


class AOIPortalNode(Node, ROSImageAcquisitionClient):
    image_acquisition_capture_cli: ServiceClient
    image_acquisition_set_parameters_cli: ServiceClient
    image_acquisition_get_status_cli: ServiceClient

    def __init__(self) -> None:
        super().__init__("open_aoi_portal")
        self.logger = self.get_logger()

        with Client.auto_index_client:
            ui.page(HOME_PAGE, title=f"Home | {APP_TITLE}")(get_view_home(self))
            ui.page(ACCESS_PAGE, title=f"Access | {APP_TITLE}")(get_view_access(self))
            ui.page(DEVICES_PAGE, title=f"Devices | {APP_TITLE}")(
                get_view_devices(self)
            )
            ui.page(MODULES_PAGE, title=f"Modules | {APP_TITLE}")(
                get_view_modules(self)
            )
            ui.page(TEMPLATES_PAGE, title="Template | AOI Portal")(
                get_view_template(self)
            )
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

        def acquire_service(name: str, property_name: str, msg):
            cli = self.create_client(msg, name)
            setattr(self, property_name, cli)
            while not cli.wait_for_service(timeout_sec=1.0):
                self.logger.info(f"Service {name} not available, waiting again...")

        acquire_service(
            "image_acquisition/capture",
            "image_acquisition_capture_cli",
            ImageAcquisition,
        )
        acquire_service(
            "image_acquisition/get_status",
            "image_acquisition_get_status_cli",
            ServiceStatus,
        )
        acquire_service(
            "image_acquisition/set_parameters",
            "image_acquisition_set_parameters_cli",
            SetParameters,
        )


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
    favicon="🚀",
    title=APP_TITLE,
    storage_secret=STORAGE_SECRET,
    uvicorn_logging_level="info",
    reload=False,  # TODO: fix reloading :(
)
