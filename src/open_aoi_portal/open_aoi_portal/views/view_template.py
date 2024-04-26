import logging
from functools import partial
from typing import Optional

from rclpy.node import Node
from nicegui import ui, app
from fastapi.responses import RedirectResponse
from PIL import Image

from open_aoi_core.constants import ImageAcquisitionConstants
from open_aoi_core.exceptions import AuthException, ROSServiceError
from open_aoi_core.controllers.template import TemplateController
from open_aoi_core.controllers.accessor import AccessorController
from open_aoi_core.controllers.camera import CameraController
from open_aoi_core.models import TITLE_LIMIT
from open_aoi_portal.common import (
    scale,
    confirm,
    inject_header,
    inject_text_field,
    to_thread,
    get_session,
    ACCESS_PAGE,
    CONTROL_ZONE_PAGE,
)

logger = logging.getLogger("ui.devices")


def get_view(node: Node):
    def view() -> Optional[RedirectResponse]:
        # -----------------------------------------------
        # Handlers
        def _handle_create_template():
            try:
                assert template_title.validate()
                assert template_image is not None
            except AssertionError:
                ui.notify("Required values are missing", type="negative")
                return

            try:
                template = template_controller.create(
                    template_title.value.strip(), accessor
                )
                template.publish_image(template_image)
                template_controller.commit()
            except Exception as e:
                logger.exception(e)
                ui.notify("Failed to create template")
                return

            ui.notify(f"Template {template.title} created!", type="positive")
            _inject_template_list()

        def _handle_delete_template(template: TemplateController._model):
            def execute():
                try:
                    template_controller.delete(template)
                    template_controller.commit()
                except Exception as e:
                    logger.exception(e)
                    ui.notify("Failed to delete template!", type="negative")
                    return

                ui.notify("Template was deleted!", type="positive")
                _inject_template_list()

            confirm("Are you sure?", execute)

        async def _handle_preview_template(template: TemplateController._model):
            try:
                im = template.materialize_image()
            except Exception as e:
                logger.exception(e)
                ui.notify("Failed to open template!", type="negative")
                return

            with ui.dialog() as dialog, ui.card():
                ui.interactive_image(im)
                with ui.row().classes("w-full justify-end"):
                    ui.button("Close", on_click=dialog.close, color="white")

            dialog.open()

        async def _handle_capture_image():
            nonlocal template_image

            try:
                assert camera_selection.validate()
            except AssertionError:
                ui.notify("Camera is required", type="negative")
                return

            capture_image.disable()
            try:
                camera = camera_controller.retrieve(camera_selection.value)
            except Exception as e:
                logger.exception(e)
                ui.notify("Failed to get camera!", type="negative")
                return
            try:
                im, error, error_description = await to_thread(
                    node.image_acquisition_capture_image,
                    camera_ip_address=camera.ip_address,
                    camera_emulation_mode=True,
                )
            except ROSServiceError as e:
                ui.notify(str(e), type="warning")
                capture_image.enable()
                return

            if error != ImageAcquisitionConstants.Error.NONE:
                ui.notify(error_description, type="negative")
                capture_image.enable()
                return

            if im is None:
                ui.notify("Failed to capture image", type="warning")
                return

            im = Image.fromarray(im)
            template_image = im
            template_image_element.set_source(scale(im, 600))

            capture_image.enable()

        # Local injections
        def _inject_template_list():
            template_list_container.clear()
            template_list = template_controller.list()

            with template_list_container:
                if len(template_list):
                    for template in template_list:
                        partial_preview = partial(_handle_preview_template, template)
                        partial_delete = partial(_handle_delete_template, template)
                        with ui.item().props("clickable"):
                            with ui.item_section():
                                with ui.row():
                                    ui.label(template.title)
                                    ui.space()
                                    ui.button(
                                        icon="edit",
                                        on_click=(
                                            lambda t: lambda: ui.open(
                                                CONTROL_ZONE_PAGE.format(
                                                    template_id=t.id
                                                )
                                            )
                                        )(template),
                                    ).props("size=sm")
                                    ui.button(
                                        icon="preview",
                                        on_click=partial_preview,
                                    ).props("size=sm")
                                    ui.button(
                                        "Remove",
                                        color="negative",
                                        on_click=partial_delete,
                                    ).props("size=sm")
                else:
                    with template_list_container:
                        with ui.card().classes("w-full bg-primary text-white"):
                            ui.markdown("**No templates to show**")

        # -----------------------------------------------

        session = get_session()
        access_controller = AccessorController(session)
        template_controller = TemplateController(session)
        camera_controller = CameraController(session)
        try:
            accessor = access_controller.identify_session_accessor(app.storage.user)
        except AuthException:
            return RedirectResponse(ACCESS_PAGE)

        inject_header()

        try:
            camera_list = camera_controller.list()
        except Exception as e:
            logger.exception(e)
            ui.notify("Failed to get camera list!", type="negative")
            return

        with ui.column().classes("w-full"):
            ui.markdown("### **Templates**")
            ui.markdown("#### **Template configuration**")
            template_title = inject_text_field(
                "Template title", "Enter any value...", TITLE_LIMIT
            )
            camera_selection = ui.select(
                dict([(c.id, c.title) for c in camera_list]),
                label="Camera",
                validation={"Value is required": lambda value: value is not None},
            ).classes("w-full")

            template_image = None
            with ui.row().classes("justify-center w-full"):
                template_image_element = ui.interactive_image()

            with ui.row().classes("w-full"):
                ui.space()

                capture_image = ui.button(
                    "Take picture", on_click=_handle_capture_image, icon="photo_camera"
                )
                ui.button(
                    "Save",
                    on_click=_handle_create_template,
                )

        ui.markdown("#### **Registered templates**")
        template_list_container = ui.list().classes("w-full").props("dense")
        _inject_template_list()

    return view
