"""
    This view define module upload page. User is permitted to upload custom code which will be executed to perform 
    product inspection. Modules (a.k.a inspection handlers) are stored in blob storage and are related to exactly one
    defect type. Inspection handler description is filled from documentation string.
"""

import logging
from typing import Optional
from functools import partial

from nicegui import ui, app
from fastapi.responses import RedirectResponse

from open_aoi_core.constants import SystemLimit
from open_aoi_core.models import InspectionHandlerModel, DefectTypeModel
from open_aoi_core.services import StandardClient
from open_aoi_core.controllers.inspection_handler import InspectionHandlerController
from open_aoi_core.controllers.accessor import AccessorController
from open_aoi_core.controllers.defect_type import DefectTypeController
from open_aoi_core.exceptions import (
    AuthenticationException,
    SystemIntegrityException,
    AssetIntegrityException,
)
from open_aoi_portal.settings import ACCESS_PAGE, HOME_PAGE
from open_aoi_portal.common import (
    safe_operation,
    safe_view,
    confirm,
    inject_header,
    inject_text_field,
    get_session,
)

logger = logging.getLogger("ui.modules")


ICON_VALID_MODULE = "🟢"
ICON_INVALID_MODULE = "🟡"
IS_STORE_CONNECTED = True


def get_view(node: StandardClient):
    @safe_view
    async def view() -> Optional[RedirectResponse]:
        session = get_session()

        accessor_controller = AccessorController(session)
        defect_type_controller = DefectTypeController(session)
        inspection_handler_controller = InspectionHandlerController(session)

        try:
            accessor = accessor_controller.identify_session_accessor(app.storage.user)
            assert accessor.role.allow_system_view
            assert accessor.role.allow_system_operations
        except AssertionError:
            return RedirectResponse(HOME_PAGE)
        except AuthenticationException:
            return RedirectResponse(ACCESS_PAGE)

        # Define functions here to access ui elements directly
        # -------------------------------------------------------------------------
        # Handlers: defect type

        @safe_operation
        async def _handle_defect_type_create():
            """Handles defect creation logic"""
            try:
                assert defect_type_title_input.validate()
                assert defect_type_description_input.validate()
            except AssertionError:
                ui.notify("Required parameters are missing.", type="warning")
                return

            title = defect_type_title_input.value.strip()
            description = defect_type_description_input.value.strip()

            try:
                defect_type_controller.create(title, description)
                defect_type_controller.commit()
            except Exception as e:
                logger.exception(e)
                ui.notify("Failed to create defect type.", type="negative")
                return

            ui.notify("New defect type created.", type="positive")

            await _inject_defect_list()

        @safe_operation
        async def _handle_defect_type_delete(defect_type: DefectTypeModel):
            """Handles defect type deletion after confirmation"""

            @safe_operation
            async def _delete():
                try:
                    defect_type_controller.delete(defect_type)
                    defect_type_controller.commit()
                except SystemIntegrityException as e:
                    logger.exception(e)
                    ui.notify(str(e), type="negative")
                    return

                ui.notify("Defect type was deleted.", type="positive")

                await _inject_defect_list()

            confirm(
                f"You are about to delete defect type {defect_type.title}. Are you sure?",
                _delete,
            )

        # Handlers: module
        @safe_operation
        async def _handle_module_upload_request(
            inspection_handler: InspectionHandlerModel,
        ):
            """Create dialog to upload files and setup upload process handler"""
            with ui.dialog() as dialog, ui.card().classes("w-[600px]"):
                ui.markdown("#### **Upload source**")
                ui.upload(
                    on_upload=partial(
                        _handle_module_upload_process, inspection_handler
                    ),
                    max_files=1,
                ).classes("w-full")
                with ui.row().classes("w-full justify-end"):
                    ui.button("Cancel", on_click=dialog.close, color="white")

            dialog.open()

        @safe_operation
        async def _handle_module_upload_process(  # Order of args is important due to partials
            inspection_handler: InspectionHandlerModel, event
        ):
            """Handles module upload process with source validation"""

            content = event.content.read()
            try:
                valid, error = inspection_handler.validate_source(content)
                if not valid:
                    ui.notify(error, type="negative")
                    return
                inspection_handler.publish_source(content)
                inspection_handler_controller.commit()
            except AssetIntegrityException as e:
                logger.exception(e)
                ui.notify(str(e), type="negative")
                return

            ui.notify(f"Uploaded {event.name}.", type="positive")

            await _inject_module_list()

        @safe_operation
        async def _handle_module_download_request(
            inspection_handler: InspectionHandlerModel,
        ):
            """Materialize module and initiate download"""
            try:
                content = inspection_handler.materialize_source()
            except Exception as e:
                logger.exception(e)
                ui.notify("Failed to obtain module source.", type="negative")
                return

            ui.download(content, f"{inspection_handler.title}.py")

        @safe_operation
        async def _handle_module_create():
            """Handles module database record creation"""
            try:
                assert module_title_input.validate()
                assert module_defect_type_selection.validate()
            except AssertionError:
                ui.notify("Some required parameters are missing", type="warning")
                return

            title = module_title_input.value.strip()

            try:
                defect_type = defect_type_controller.retrieve(
                    module_defect_type_selection.value
                )
                inspection_handler_controller.create(
                    title=title,
                    defect_type=defect_type,
                )
                inspection_handler_controller.commit()
            except Exception as e:
                logger.exception(e)
                ui.notify("Failed to create module.", type="negative")
                return

            ui.notify("New module created", type="positive")

            await _inject_module_list()

        @safe_operation
        async def _handle_module_delete(
            inspection_handler: InspectionHandlerModel,
        ):
            """Handles module deletion with confirmation"""

            @safe_operation
            async def _delete():
                try:
                    inspection_handler_controller.delete(inspection_handler)
                    inspection_handler_controller.commit()
                except SystemIntegrityException as e:
                    logger.exception(e)
                    ui.notify(str(e), type="negative")
                    return

                ui.notify("Module was deleted.", type="positive")

                await _inject_module_list()

            confirm(
                f"You are about to delete module {inspection_handler.title}. Are you sure?",
                _delete,
            )

        # Local injections
        @safe_operation
        async def _inject_defect_list():
            """Generate list of defect types"""

            defect_types_container.clear()
            try:
                defect_types = defect_type_controller.list()
            except:
                ui.notify("Failed to get defect types.", type="negative")
                return

            with defect_types_container:
                if len(defect_types):
                    with ui.list().classes("w-full"):
                        for defect_type in defect_types:
                            with ui.item().props("clickable").classes("w-full"):
                                with ui.item_section():
                                    ui.item_label(defect_type.title)
                                    ui.item_label(defect_type.description).props(
                                        "caption"
                                    )
                                with ui.item_section().props("side"):
                                    ui.button(
                                        on_click=partial(
                                            _handle_defect_type_delete, defect_type
                                        ),
                                        icon="close",
                                        color="negative",
                                    ).props(
                                        "size=sm",
                                    )
                else:
                    with ui.card().classes("w-full bg-primary text-white"):
                        ui.markdown("**No defect types to show.**")

            # Update defect types options for module creation part
            options = dict([(dt.id, dt.title) for dt in defect_types])
            module_defect_type_selection.set_options(options)

        @safe_operation
        async def _inject_module_list():
            """Generate list of available modules"""

            modules_container.clear()
            try:
                inspection_handlers = inspection_handler_controller.list_nested()
            except Exception as e:
                logger.exception(e)
                ui.notify("Failed to get modules.", type="negative")
                return

            with modules_container:
                if len(inspection_handlers):
                    with ui.list().classes("w-full"):
                        for inspection_handler in inspection_handlers:
                            with ui.item().props("clickable").classes("w-full"):
                                with ui.item_section():
                                    with ui.row():
                                        ui.markdown(
                                            f"{ICON_INVALID_MODULE if inspection_handler.blob is None else ICON_VALID_MODULE} **{inspection_handler.title}** {inspection_handler.defect_type.title}"
                                        )
                                        ui.space()
                                        ui.button(
                                            on_click=partial(
                                                _handle_module_upload_request,
                                                inspection_handler,
                                            ),
                                            color="white",
                                            icon="upload",
                                        ).props(
                                            "size=sm",
                                        )
                                        download = ui.button(
                                            on_click=partial(
                                                _handle_module_download_request,
                                                inspection_handler,
                                            ),
                                            color="white",
                                            icon="download",
                                        ).props(
                                            "size=sm",
                                        )
                                        if inspection_handler.blob is None:
                                            download.disable()
                                        ui.button(
                                            on_click=partial(
                                                _handle_module_delete,
                                                inspection_handler,
                                            ),
                                            icon="close",
                                            color="negative",
                                        ).props("size=sm")
                                    with ui.card().classes(
                                        "w-full bg-grey-8 text-white"
                                    ):
                                        ui.html(
                                            inspection_handler.description.strip().replace(
                                                "\n", "<br>"
                                            )
                                        )

                else:
                    with ui.card().classes("w-full bg-primary text-white"):
                        ui.markdown("**No modules to show**")

        # -------------------------------------------------------------------------

        await inject_header(accessor)
        with ui.column().classes("w-full"):
            ui.markdown("#### **Modules and Defects**")
            ui.markdown(
                (
                    "This page allows to upload custom inspection algorithms written in python. Each algorithm should control for one defect type. Refer project documentation for more details."
                    "Overrides for modules are not permitted. In order to create new version of module create new module. "
                )
            )
            ui.markdown("##### **Defects**")
            ui.markdown("Define defect here to assign them to modules.")
            with ui.column().classes("w-full"):
                defect_type_title_input = await inject_text_field(
                    "Defect title", "Enter defect title", SystemLimit.TITLE_LENGTH
                )
                defect_type_description_input = await inject_text_field(
                    "Defect description",
                    "Enter defect description",
                    SystemLimit.DESCRIPTION_LENGTH,
                )
                with ui.row().classes("w-full"):
                    ui.space()
                    ui.button(
                        "Create",
                        color="positive",
                        on_click=_handle_defect_type_create,
                    )
            defect_types_container = ui.row().classes("w-full")

            ui.markdown("##### **Modules**")
            ui.markdown(
                "Upload custom inspection code here! For more information please refer project documentation. Each module may provide own documentation, which will be visible after upload."
            )
            with ui.column().classes("w-full"):
                module_title_input = await inject_text_field(
                    "Module title", "Enter module title", SystemLimit.TITLE_LENGTH
                )
                module_defect_type_selection = ui.select(
                    {},
                    label="Detectable defect type",
                    validation={
                        "Defect type is required": lambda value: value is not None
                    },
                ).classes("w-full")

                with ui.row().classes("w-full"):
                    ui.space()
                    ui.button(
                        "Create", color="positive", on_click=_handle_module_create
                    )
            modules_container = ui.row().classes("w-full")

            await _inject_module_list()
            await _inject_defect_list()

    return view
