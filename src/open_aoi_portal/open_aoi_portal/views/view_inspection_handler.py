"""
    This view define module upload page. User is permitted to upload custom code which will be executed to perform 
    product inspection. Modules (a.k.a inspection handlers) are stored in blob storage and are related to exactly one
    defect type.
"""

import logging
from typing import Optional
from functools import partial

from rclpy.node import Node
from nicegui import ui, app
from fastapi.responses import RedirectResponse

from open_aoi_core.constants import SystemLimit
from open_aoi_core.exceptions import (
    AuthenticationException,
    SystemIntegrityException,
    AssetIntegrityException,
)
from open_aoi_core.controllers.inspection_handler import InspectionHandlerController
from open_aoi_core.controllers.accessor import AccessorController
from open_aoi_core.controllers.defect_type import DefectTypeController
from open_aoi_portal.common import (
    confirm,
    inject_header,
    inject_text_field,
    get_session,
    ACCESS_PAGE,
    HOME_PAGE,
)

logger = logging.getLogger("ui.modules")


ICON_VALID_MODULE = "🟢"
ICON_INVALID_MODULE = "🟡"
IS_STORE_CONNECTED = True


def get_view(node: Node):
    def view() -> Optional[RedirectResponse]:
        session = get_session()

        accessor_controller = AccessorController(session)
        defect_type_controller = DefectTypeController(session)
        inspection_handler_controller = InspectionHandlerController(session)

        try:
            accessor = accessor_controller.identify_session_accessor(app.storage.user)
            assert accessor.role.allow_system_operations
        except AssertionError:
            return RedirectResponse(HOME_PAGE)
        except AuthenticationException:
            return RedirectResponse(ACCESS_PAGE)
        except Exception as e:
            logger.exception(e)
            ui.notify(
                "Unexpected exception.",
                type="negative",
            )
            return

        # Define functions here to access ui elements directly
        # -------------------------------------------------------------------------
        # Handlers: defect type
        def _handle_defect_type_create():
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

            _inject_defect_list()

        def _handle_defect_type_delete(defect_type):
            """Handles defect type deletion after confirmation"""

            def _delete():
                try:
                    defect_type_controller.delete(defect_type)
                    defect_type_controller.commit()
                except SystemIntegrityException as e:
                    ui.notify(str(e), type="negative")
                    return
                except Exception as e:
                    logger.exception(e)
                    ui.notify(
                        "Unexpected exception.",
                        type="negative",
                    )
                    return

                ui.notify("Defect type was deleted.", type="positive")

                _inject_defect_list()

            confirm(
                f"You are about to delete defect type {defect_type.title}. Are you sure?",
                _delete,
            )

        # Handlers: module
        def _handle_module_upload_request(inspection_handler):
            """Create dialog to upload files and setup upload process handler"""

            with ui.dialog() as dialog, ui.card().classes("w-[600px]"):
                ui.markdown("#### **Upload source**")
                ui.upload(
                    on_upload=partial(
                        lambda e: _handle_module_upload_process(e, inspection_handler)
                    ),
                    max_files=1,
                ).classes("w-full")
                with ui.row().classes("w-full justify-end"):
                    ui.button("Cancel", on_click=dialog.close, color="white")

            dialog.open()

        def _handle_module_upload_process(e, inspection_handler):
            """Handles module upload process with source validation"""

            content = e.content.read()
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
            except Exception as e:
                logger.exception(e)
                ui.notify(
                    "Unexpected exception.",
                    type="negative",
                )
                return

            ui.notify(f"Uploaded {e.name}.", type="positive")

            _inject_module_list()

        def _handle_module_download_request(inspection_handler):
            """Materialize module and initiate download"""
            try:
                content = inspection_handler.materialize_source()
            except Exception as e:
                logger.exception(e)
                ui.notify("Failed to obtain module source.", type="negative")
                return

            ui.download(content, f"{inspection_handler.title}.py")

        def _handle_module_create():
            """Handles module database record creation"""
            try:
                assert module_title_input.validate()
                assert module_description_input.validate()
                assert module_defect_type_selection.validate()
            except AssertionError:
                ui.notify("Some required parameters are missing", type="warning")
                return

            title = module_title_input.value.strip()
            description = module_description_input.value.strip()

            try:
                defect_type = defect_type_controller.retrieve(
                    module_defect_type_selection.value
                )
                inspection_handler_controller.create(
                    title=title,
                    description=description,
                    defect_type=defect_type,
                )
                inspection_handler_controller.commit()
            except Exception as e:
                logger.exception(e)
                ui.notify("Failed to create module.", type="negative")
                return

            ui.notify("New module created", type="positive")

            _inject_module_list()

        def _handle_module_delete(inspection_handler):
            """Handles module deletion with confirmation"""

            def _delete():
                try:
                    inspection_handler_controller.delete(inspection_handler)
                    inspection_handler_controller.commit()
                except SystemIntegrityException as e:
                    ui.notify(str(e), type="negative")
                    return
                except Exception as e:
                    logger.exception(e)
                    ui.notify(
                        "Unexpected exception.",
                        type="negative",
                    )
                    return

                ui.notify("Module was deleted.", type="positive")

                _inject_module_list()

            confirm(
                f"You are about to delete module {inspection_handler.title}. Are you sure?",
                _delete,
            )

        # Local injections
        def _inject_defect_list():
            """Generate list of defect types"""

            defect_types_container.clear()
            try:
                defect_types = defect_type_controller.list()
            except:
                ui.notify("Failed to get defect types.", type="negative")
                return

            with defect_types_container:
                if len(defect_types):
                    with ui.scroll_area().classes("w-full"):
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

        def _inject_module_list():
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
                    with ui.scroll_area().classes("w-full"):
                        with ui.list().classes("w-full"):
                            for inspection_handler in inspection_handlers:
                                with ui.item().props("clickable").classes("w-full"):
                                    with ui.item_section():
                                        ui.item_label(
                                            f"{ICON_INVALID_MODULE if inspection_handler.blob is None else ICON_VALID_MODULE} {inspection_handler.defect_type.title} | {inspection_handler.title}"
                                        )
                                        ui.item_label(
                                            inspection_handler.description
                                        ).props("caption")
                                    with ui.item_section().props("side"):
                                        with ui.row():
                                            ui.button(
                                                on_click=partial(
                                                    _handle_module_upload_request,
                                                    inspection_handler,
                                                ),
                                                icon="upload",
                                            ).props(
                                                "size=sm",
                                            )
                                            download = ui.button(
                                                on_click=partial(
                                                    _handle_module_download_request,
                                                    inspection_handler,
                                                ),
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
                                            ).props(
                                                "size=sm",
                                            )
                else:
                    with ui.card().classes("w-full bg-primary text-white"):
                        ui.markdown("**No modules to show**")

        # -------------------------------------------------------------------------

        inject_header(accessor)
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
            with ui.grid(columns=2).classes("w-full"):
                with ui.column():
                    defect_type_title_input = inject_text_field(
                        "Defect title", "Enter defect title", SystemLimit.TITLE_LENGTH
                    )
                    defect_type_description_input = inject_text_field(
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
                defect_types_container = ui.row()

            ui.markdown("##### **Modules**")
            ui.markdown(
                "Upload custom inspection code here! For more information please refer project documentation."
            )
            with ui.grid(columns=2).classes("w-full"):
                with ui.column():
                    module_title_input = inject_text_field(
                        "Module title", "Enter module title", SystemLimit.TITLE_LENGTH
                    )
                    module_description_input = inject_text_field(
                        "Module description",
                        "Enter module description",
                        SystemLimit.DESCRIPTION_LENGTH,
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
                modules_container = ui.row()

            _inject_module_list()
            _inject_defect_list()

    return view
