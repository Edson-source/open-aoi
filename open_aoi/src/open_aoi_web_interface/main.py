import logging

from nicegui import ui
from open_aoi.settings import STORAGE_SECRET, WEB_INTERFACE_PORT
from open_aoi_web_interface.settings import *

# from open_aoi_web_interface.views.view_access import view as view_access
from open_aoi_web_interface.views.view_home import view as view_home
from open_aoi_web_interface.views.view_devices import view as view_devices

# from open_aoi_web_interface.views.view_inspection_profile import (
#     view as view_inspection_profile,
# )
# from open_aoi_web_interface.views.view_template import view as view_template
# from open_aoi_web_interface.views.view_control_zone_editor import (
#     view as view_control_zone_editor,
# )
# from open_aoi_web_interface.views.view_inspection_live import (
#     view as view_inspection_live,
# )
# from open_aoi_web_interface.views.view_inspection_log import (
#     view as view_inspection_log,
# )
from open_aoi_web_interface.views.view_modules import view as view_modules

ui.page("/", title="Home | AOI Portal")(view_home)
ui.page(DEVICES_PAGE, title="Devices | AOI Portal")(view_devices)
# ui.page("/access", title="Access | AOI Portal")(view_access)
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
ui.page(
    MODULES_PAGE,
    title="Modules | AOI Portal",
)(view_modules)
# ui.page(
#     "/template/test/control_zone",
#     title="Control zone editor | AOI Portal",
# )(view_control_zone_editor)

logging.basicConfig(level=logging.INFO)
ui.run(
    port=WEB_INTERFACE_PORT,
    storage_secret=STORAGE_SECRET,
    uvicorn_logging_level="info",
    favicon="🚨",
    title="Open AOI",
)
