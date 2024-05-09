"""
    View provide inspection zone editor. Inspection zone is defined over template with 2 dots (2 clicks in the image, 3rd click clears editor). 
    Editor also have basic image navigation and zoom.
"""

import logging
from typing import Optional
from functools import partial

from nicegui import ui, app
from fastapi.responses import RedirectResponse

from open_aoi_core.utils_basic import crop_stat_image
from open_aoi_core.constants import SystemLimit
from open_aoi_core.services import StandardClient
from open_aoi_core.exceptions import AuthenticationException, SystemIntegrityException
from open_aoi_core.models import InspectionZoneModel
from open_aoi_core.controllers.accessor import AccessorController
from open_aoi_core.controllers.template import TemplateController
from open_aoi_core.controllers.connected_component import ConnectedComponentController
from open_aoi_core.controllers.inspection_zone import InspectionZoneController
from open_aoi_core.controllers.inspection_handler import InspectionHandlerController
from open_aoi_core.controllers.inspection_target import InspectionTargetController
from open_aoi_portal.settings import ACCESS_PAGE, HOME_PAGE
from open_aoi_portal.common import (
    confirm,
    get_session,
    InspectionZoneManager,
    inject_header,
    inject_text_field,
    safe_operation,
    safe_view,
)


logger = logging.getLogger("ui.inspection_zone_editor")


def get_view(node: StandardClient):
    @safe_view
    async def view(template_id: int) -> Optional[RedirectResponse]:
        session = get_session()

        accessor_controller = AccessorController(session)
        template_controller = TemplateController(session)
        inspection_zone_controller = InspectionZoneController(session)
        connected_component_controller = ConnectedComponentController(session)
        inspection_handler_controller = InspectionHandlerController(session)
        inspection_target_controller = InspectionTargetController(session)

        try:
            accessor = accessor_controller.identify_session_accessor(app.storage.user)
            assert accessor.role.allow_system_view
            assert accessor.role.allow_system_operations
        except AssertionError:
            return RedirectResponse(HOME_PAGE)
        except AuthenticationException:
            return RedirectResponse(ACCESS_PAGE)

        await inject_header(accessor)

        # -----------------------------------
        # Handlers
        @safe_operation
        async def _handle_inspection_zone_create():
            """Create inspection zone with connected component from editor"""

            cc = manager.inspection_zone_connected_component()

            try:
                assert inspection_zone_title.validate()
                assert inspection_handler_selection.validate()
                assert cc is not None
            except AssertionError:
                ui.notify(
                    "Inspection zone require a title. inspection handler and selected zone in the template image.",
                    type="negative",
                )
                return

            try:
                inspection_handler = inspection_handler_controller.retrieve(
                    inspection_handler_selection.value
                )
                assert inspection_handler is not None
            except AssertionError as e:
                logger.exception(e)
                ui.notify(
                    "Failed to retrieve related inspection handler.", type="negative"
                )
                return

            inspection_zone = inspection_zone_controller.create(
                inspection_zone_title.value.strip(), template, accessor
            )
            connected_component = connected_component_controller.create(
                cc[0], cc[1], cc[2], cc[3], inspection_zone
            )
            inspection_target = inspection_target_controller.create(
                inspection_handler, inspection_zone
            )
            inspection_zone_controller.commit()

            ui.notify("Inspection zone created.", type="positive")
            await _inject_inspection_zone_list()

        @safe_operation
        async def _handle_inspection_zone_delete(inspection_zone: InspectionZoneModel):
            """Handles inspection zone deletion with confirmation"""

            @safe_operation
            async def _delete():
                try:
                    for inspection_target in inspection_zone.inspection_target_list:
                        inspection_target_controller.delete(inspection_target)
                    connected_component_controller.delete(inspection_zone.cc)
                    inspection_zone_controller.delete(inspection_zone)
                    inspection_zone_controller.commit()
                except SystemIntegrityException as e:
                    logger.exception(e)
                    ui.notify(str(e), type="negative")
                    return
                ui.notify("Inspection zone deleted.", type="positive")
                await _inject_inspection_zone_list()

            confirm(
                f"You are about to delete inspection zone {inspection_zone.title}. Are you sure?",
                _delete,
            )

        @safe_operation
        async def _handle_inspection_zone_preview(inspection_zone):
            """Crop template image and show zone preview"""
            cc = [
                inspection_zone.cc.stat_left,
                inspection_zone.cc.stat_top,
                inspection_zone.cc.stat_width,
                inspection_zone.cc.stat_height,
            ]
            cropped = crop_stat_image(template_image, cc)
            with ui.dialog() as dialog, ui.card():
                ui.interactive_image(cropped)
                with ui.row().classes("w-full justify-end"):
                    ui.button("Close", on_click=dialog.close, color="white")

            dialog.open()

        # Local injections
        @safe_operation
        async def _inject_inspection_zone_list():
            """Generate list of available inspection zones"""
            inspection_zone_container.clear()
            inspection_zone_list = template.inspection_zone_list
            if len(inspection_zone_list):
                with inspection_zone_container:
                    for inspection_zone in inspection_zone_list:
                        with ui.item().classes("w-full").props("clickable"):
                            with ui.item_section():
                                with ui.row():
                                    ui.label(f"{inspection_zone.title}")
                                    ui.space()
                                    ui.button(
                                        icon="preview",
                                        on_click=partial(
                                            _handle_inspection_zone_preview,
                                            inspection_zone,
                                        ),
                                        color="white",
                                    ).props("size=sm")
                                    ui.button(
                                        "Remove",
                                        color="negative",
                                        on_click=partial(
                                            _handle_inspection_zone_delete,
                                            inspection_zone,
                                        ),
                                    ).props("size=sm")
            else:
                with inspection_zone_container:
                    with ui.card().classes("w-full bg-primary text-white"):
                        ui.markdown("**No zones to show.**")

        # -----------------------------------

        try:
            template = template_controller.retrieve(template_id)
            inspection_handler_list = inspection_handler_controller.list()
        except Exception as e:
            logger.exception(e)
            ui.notify("Failed to get data from database.", type="negative")
            return

        with ui.column().classes("w-full"):
            ui.markdown("### **Inspection zone editor**")
            ui.markdown(
                (
                    "Inspection zone editor is used to define inspection zones, where selected module (inspection handler) should be applied. "
                    "Each module may have certain rules to define valid inspection zone (how zone should be selected on template, what should be in the zone, etc). "
                    "Refer module documentation for more details. "
                )
            )
            ui.markdown(f"#### **Template: {template.title}**")

            try:
                template_image = template.materialize_image()
            except Exception as e:
                logger.exception(e)
                ui.notify("Failed to get template image.", type="negative")
                return

            manager = InspectionZoneManager(
                template_image, [100, template_image.size[0]]
            )
            docs = dict(
                [
                    (handler.id, handler.description)
                    for handler in inspection_handler_list
                ]
            )
            with ui.grid(columns=4).classes("justify-left w-full"):
                with ui.column().classes("col-span-3"):
                    await manager.inject_editor()
                with ui.list().classes("col-span-1").props(
                    "dense"
                ) as inspection_zone_container:
                    await _inject_inspection_zone_list()

            inspection_zone_title = await inject_text_field(
                "Title",
                "Enter short name for this inspection zone",
                SystemLimit.TITLE_LENGTH,
            )
            inspection_handler_selection = ui.select(
                label="Inspection handler (module)",
                options=dict(
                    [(handler.id, handler.title) for handler in inspection_handler_list]
                ),
                validation={"Module is required": lambda value: value is not None},
                on_change=lambda e: inspection_handler_display.set_text(
                    docs.get(inspection_handler_selection.value) or "No documentation"
                ),
            ).classes("w-full")
            inspection_handler_display = ui.label(
                "Documentation will be available here."
            ).classes("text-secondary")

            with ui.row().classes("w-full"):
                ui.space()
                ui.button(
                    "Save", on_click=_handle_inspection_zone_create, color="positive"
                )

    return view
