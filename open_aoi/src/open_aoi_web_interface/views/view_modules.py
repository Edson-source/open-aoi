# TODO: FIX LAMBDA VALUEs!
# TODO: On upload rerender module list
import logging
from typing import Optional

from nicegui import ui
from fastapi.responses import RedirectResponse

from open_aoi.models import TITLE_LIMIT, DESCRIPTION_LIMIT
from open_aoi.exceptions import AuthException, ConnectivityError, IntegrityError
from open_aoi.controllers.control_handler import ControlHandlerController
from open_aoi.controllers.defect_type import DefectTypeController
from open_aoi_web_interface.views.common import (
    confirm,
    inject_header,
    inject_text_field,
    ACCESS_PAGE,
    access_guard,
)

logger = logging.getLogger("ui.modules")


IS_STORE_CONNECTED = True


# Connection watcher
def _handle_store_connection_test():
    verbose = True

    def _watchdog():
        global IS_STORE_CONNECTED
        nonlocal verbose
        try:
            ControlHandlerController.test_store_connection()
            if not IS_STORE_CONNECTED:
                ui.notify("Store connected!", type="positive")
                IS_STORE_CONNECTED = True
                verbose = True
        except ConnectivityError as e:
            if verbose:
                ui.notify(str(e), type="negative")
            IS_STORE_CONNECTED = False
            verbose = False

    ui.timer(1, _watchdog)


def view() -> Optional[RedirectResponse]:
    try:
        accessor = access_guard()
    except AuthException:
        return RedirectResponse(ACCESS_PAGE)

    # Define functions here to access ui elements directly
    # -------------------------------------------------------------------------
    # Handlers
    # Handlers: defect type
    def _handle_defect_type_create(*callbacks: callable):
        try:
            assert defect_type_title_input.validate()
            assert defect_type_description_input.validate()
        except AssertionError:
            ui.notify("Some required parameters are missing")
            return

        DefectTypeController.create(
            defect_type_title_input.value, defect_type_description_input.value
        )
        ui.notify("New defect type created", type="positive")
        for callback in callbacks:
            callback()

    def _handle_defect_type_delete(defect_type_id: int, *callbacks: callable):
        def _execute():
            try:
                DefectTypeController.delete_by_id(defect_type_id)
            except IntegrityError as e:
                ui.notify(str(e), type="negative")
                return

            ui.notify("Deleted!", type="positive")
            for callback in callbacks:
                callback()

        confirm("Are you sure?", _execute)

    # Handlers: module
    def _handle_module_upload_request(control_handler_id: int):
        with ui.dialog() as dialog, ui.card().classes("w-[600px]"):
            ui.markdown("#### **Upload source**")
            ui.upload(
                on_upload=lambda e: _handle_module_upload_process(
                    e, control_handler_id
                ),
                max_files=1,
            ).classes("w-full")
            with ui.row().classes("w-full justify-end"):
                ui.button("Cancel", on_click=dialog.close, color="white")

        dialog.open()

    def _handle_module_upload_process(e, control_handler_id: int):
        logger.info(f"Received: {e.name}")
        content = e.content.read()
        valid, error = ControlHandlerController.validate_source(content)
        if not valid:
            ui.notify(error, type="negative")
            return
        control_handler = ControlHandlerController.retrieve(control_handler_id)
        ControlHandlerController.publish_source(control_handler, content)
        ui.notify(f"Uploaded {e.name}")

    def _handle_module_download_request(control_handler_id: int):
        print(control_handler_id)
        control_handler = ControlHandlerController.retrieve(control_handler_id)
        source = ControlHandlerController.materialize_for_download(control_handler)
        ui.download(source, "module.py")

    def _handle_module_create(*callbacks: callable):
        try:
            assert module_title_input.validate()
            assert module_description_input.validate()
            assert module_defect_type_selection.validate()
        except AssertionError:
            ui.notify("Some required parameters are missing")
            return

        defect_type = DefectTypeController.retrieve(module_defect_type_selection.value)
        control_handler = ControlHandlerController.create(
            title=module_title_input.value,
            description=module_description_input.value,
            defect_type=defect_type,
        )

        ui.notify("New module created", type="positive")
        for callback in callbacks:
            callback()

    def _handle_module_delete(control_handler_id: int, *callbacks: callable):
        def _execute():
            try:
                ControlHandlerController.delete_by_id(control_handler_id)
            except IntegrityError as e:
                ui.notify(str(e), type="negative")
                return
            ui.notify("Deleted!", type="positive")
            for callback in callbacks:
                callback()

        confirm("Are you sure?", _execute)

    # Local injections
    def _inject_defect_list():
        defect_types_container.clear()

        defect_types = DefectTypeController.list()
        with defect_types_container:
            if len(defect_types):
                with ui.scroll_area().classes("w-full"):
                    with ui.list().classes("w-full"):
                        for defect_type in defect_types:
                            with ui.item().classes("w-full"):
                                with ui.item_section():
                                    ui.item_label(defect_type.title)
                                    ui.item_label(defect_type.description).props(
                                        "caption"
                                    )
                                with ui.item_section().props("side"):
                                    ui.button(
                                        on_click=lambda: _handle_defect_type_delete(
                                            defect_type.id,
                                            lambda: _inject_defect_list(),
                                            lambda: _update_module_type_defect_selection(),
                                        ),
                                        icon="close",
                                        color="negative",
                                    ).props(
                                        "size=sm",
                                    )
            else:
                with ui.card().classes("w-full bg-primary text-white"):
                    ui.markdown("**No defect types to show**")

    def _inject_module_list():
        modules_container.clear()

        control_handlers = ControlHandlerController.list_nested()
        with modules_container:
            if len(control_handlers):
                with ui.scroll_area().classes("w-full"):
                    with ui.list().classes("w-full"):
                        for control_handler in control_handlers:
                            with ui.item().classes("w-full"):
                                with ui.item_section():
                                    ui.item_label(
                                        f"{'🟢' if control_handler.handler_blob is not None else '🟡'} {control_handler.defect_type.title} | {control_handler.title}"
                                    )
                                    ui.item_label(control_handler.description).props(
                                        "caption"
                                    )
                                with ui.item_section().props("side"):
                                    with ui.row():
                                        ui.button(
                                            on_click=lambda: _handle_module_upload_request(
                                                control_handler.id
                                            ),
                                            icon="upload",
                                        ).props(
                                            "size=sm",
                                        )
                                        download = ui.button(
                                            on_click=lambda: _handle_module_download_request(
                                                control_handler.id,
                                            ),
                                            icon="download",
                                        ).props(
                                            "size=sm",
                                        )
                                        if control_handler.handler_blob is None:
                                            download.disable()
                                        ui.button(
                                            on_click=lambda: _handle_module_delete(
                                                control_handler.id,
                                                lambda: _inject_module_list(),
                                            ),
                                            icon="close",
                                            color="negative",
                                        ).props(
                                            "size=sm",
                                        )
            else:
                with ui.card().classes("w-full bg-primary text-white"):
                    ui.markdown("**No modules to show**")

    # Other
    def _update_module_type_defect_selection():
        defect_types = DefectTypeController.list()
        options = dict([(dt.id, dt.title) for dt in defect_types])
        module_defect_type_selection.set_options(options)

    # -------------------------------------------------------------------------

    inject_header()
    with ui.column().classes("w-full"):
        ui.markdown("#### **Modules and Defects**")
        ui.markdown("##### **Defects**")
        ui.markdown("Define defect here to assign them to modules.")
        with ui.grid(columns=2).classes("w-full"):
            with ui.column():
                defect_type_title_input = inject_text_field(
                    "Defect title", "Enter defect title", TITLE_LIMIT
                )
                defect_type_description_input = inject_text_field(
                    "Defect description", "Enter defect description", DESCRIPTION_LIMIT
                )
                with ui.row().classes("w-full"):
                    ui.space()
                    ui.button(
                        "Create",
                        color="positive",
                        on_click=lambda: _handle_defect_type_create(
                            lambda: _inject_defect_list(),
                            lambda: _update_module_type_defect_selection(),
                        ),
                    )
            with ui.row() as defect_types_container:
                _inject_defect_list()

        ui.separator()
        ui.markdown("##### **Modules**")
        ui.markdown(
            "Upload custom inspection code here! For more information please refer user manual."
        )
        with ui.grid(columns=2).classes("w-full"):
            with ui.column():
                module_title_input = inject_text_field(
                    "Module title", "Enter module title", TITLE_LIMIT
                )
                module_description_input = inject_text_field(
                    "Module description", "Enter module description", DESCRIPTION_LIMIT
                )
                module_defect_type_selection = ui.select(
                    {},
                    label="Detectable defect type",
                    validation={
                        "Defect type is required": lambda value: value is not None
                    },
                ).classes("w-full")
                _update_module_type_defect_selection()

                with ui.row().classes("w-full"):
                    ui.space()
                    ui.button(
                        "Create",
                        color="positive",
                        on_click=lambda: _handle_module_create(
                            lambda: _inject_module_list(),
                        ),
                    )
            with ui.row() as modules_container:
                _inject_module_list()

    _handle_store_connection_test()
