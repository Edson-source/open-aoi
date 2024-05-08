"""
    This view allow to create a template by capturing image from selected camera. List of templates is also available.
"""

import logging
from functools import partial
from typing import Optional

from PIL import Image
from nicegui import ui, app
from fastapi.responses import RedirectResponse

from open_aoi_core.constants import ImageAcquisitionConstants, SystemLimit
from open_aoi_core.utils import msg_to_image
from open_aoi_core.services import StandardClient
from open_aoi_core.models import TemplateModel
from open_aoi_core.controllers.template import TemplateController
from open_aoi_core.controllers.accessor import AccessorController
from open_aoi_core.controllers.camera import CameraController
from open_aoi_portal.settings import HOME_PAGE, ACCESS_PAGE, CONTROL_ZONE_PAGE
from open_aoi_portal.common import (
    confirm,
    inject_header,
    inject_text_field,
    to_thread,
    get_session,
    safe_view,
    safe_operation,
)
from open_aoi_core.exceptions import (
    AuthenticationException,
    SystemServiceException,
    SystemIntegrityException,
    AssetIntegrityException,
)

logger = logging.getLogger("ui.template")


def get_view(node: StandardClient):

    @safe_view
    async def view() -> Optional[RedirectResponse]:
        session = get_session()

        accessor_controller = AccessorController(session)
        template_controller = TemplateController(session)
        camera_controller = CameraController(session)

        try:
            accessor = accessor_controller.identify_session_accessor(app.storage.user)
            assert accessor.role.allow_system_view
            assert accessor.role.allow_system_operations
        except AuthenticationException:
            return RedirectResponse(ACCESS_PAGE)
        except AssertionError:
            return RedirectResponse(HOME_PAGE)

        # -----------------------------------------------
        # Handlers
        @safe_operation
        async def _handle_create_template():
            """Handles template creation"""
            try:
                assert template_title.validate()
                assert template_image is not None
            except AssertionError:
                ui.notify("Required values are missing.", type="negative")
                return

            title = template_title.value.strip()

            try:
                template = template_controller.create(title, accessor)
                template.publish_image(template_image)
                template_controller.commit()
            except SystemIntegrityException as e:
                logger.exception(e)
                ui.notify(str(e), type="negative")
                return

            ui.notify(f"Template {template.title} created.", type="positive")
            await _inject_template_list()

        @safe_operation
        async def _handle_delete_template(template: TemplateModel):
            """Handles template deletion with confirmation"""

            @safe_operation
            async def _delete():
                try:
                    template_controller.delete(template)
                    template_controller.commit()
                except SystemIntegrityException as e:
                    logger.exception(e)
                    ui.notify(str(e), type="negative")
                    return

                ui.notify("Template was deleted.", type="positive")
                await _inject_template_list()

            confirm(
                f"You are about to delete template {template.title}. Are you sure?",
                _delete,
            )

        @safe_operation
        async def _handle_preview_template(template: TemplateModel):
            """Handle template preview. Materialization operation takes some time so should be async."""
            try:
                image = template.materialize_image()
            except (AssetIntegrityException, SystemIntegrityException) as e:
                logger.exception(e)
                ui.notify(f"Failed to load template. {str(e)}", type="negative")
                return

            with ui.dialog() as dialog, ui.card():
                ui.interactive_image(image)
                with ui.row().classes("w-full justify-end"):
                    ui.button("Close", on_click=dialog.close, color="white")

            dialog.open()

        @safe_operation
        async def _handle_capture_image():
            """Capture image for template"""
            nonlocal template_image

            try:
                assert camera_selection.validate()
            except AssertionError:
                ui.notify("Camera is required.", type="negative")
                return

            capture_image.disable()
            try:
                camera = camera_controller.retrieve(camera_selection.value)
                assert camera is not None
            except AssertionError as e:
                logger.exception(e)
                ui.notify("Failed to get camera.", type="negative")
                return

            try:
                response = await to_thread(
                    node.await_future,
                    node.image_acquisition_capture_image(
                        camera_ip_address=camera.ip_address,
                    ),
                )
            except SystemServiceException as e:
                logger.exception(e)
                ui.notify(str(e), type="warning")
                capture_image.enable()
                return

            if response.error != ImageAcquisitionConstants.Error.NONE:
                ui.notify(response.error_description, type="negative")
                capture_image.enable()
                return

            if response.image is None:
                ui.notify("Failed to capture image.", type="warning")
                return

            template_image = msg_to_image(response.image)
            template_image = Image.fromarray(template_image)
            template_image_element.set_source(template_image)

            capture_image.enable()

        # Local injections
        @safe_operation
        async def _inject_template_list():
            """Generate list of available templates"""
            template_list_container.clear()
            template_list = template_controller.list_nested()

            with template_list_container:
                if len(template_list):
                    for template in template_list:
                        # Define available actions for each template
                        partial_preview = partial(_handle_preview_template, template)
                        partial_delete = partial(_handle_delete_template, template)
                        partial_edit = partial(
                            ui.open, CONTROL_ZONE_PAGE.format(template_id=template.id)
                        )
                        with ui.item().props("clickable"):
                            with ui.item_section():
                                with ui.row():
                                    ui.label(
                                        f"{template.title} (inspection zones: {len(template.inspection_zone_list)})"
                                    )
                                    ui.space()
                                    ui.button(
                                        icon="edit",
                                        color="white",
                                        on_click=partial_edit,
                                    ).props("size=sm")
                                    ui.button(
                                        icon="preview",
                                        color="white",
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
                            ui.markdown("**No templates to show.**")

        # -----------------------------------------------

        await inject_header(accessor)

        try:
            camera_list = camera_controller.list()
        except Exception as e:
            logger.exception(e)
            ui.notify("Failed to get camera list.", type="negative")
            return

        with ui.column().classes("w-full"):
            ui.markdown("### **Templates**")
            ui.markdown(
                (
                    "Template is a golden image of a product. Template image may not be uploaded externally and should be captured with registered camera. "
                    "After capturing template image inspection zone editor will be available. "
                )
            )
            ui.markdown("#### **Template configuration**")
            template_title = await inject_text_field(
                "Template title", "Enter title value...", SystemLimit.TITLE_LENGTH
            )
            camera_selection = ui.select(
                dict([(c.id, c.title) for c in camera_list]),
                label="Camera",
                validation={"Camera is required": lambda value: value is not None},
            ).classes("w-full")

            template_image = None
            with ui.row().classes("justify-center w-full"):
                template_image_element = ui.interactive_image()

            with ui.row().classes("w-full"):
                ui.space()
                capture_image = ui.button(
                    "Capture image",
                    on_click=_handle_capture_image,
                    icon="photo_camera",
                    color="white",
                )
                ui.button("Save", on_click=_handle_create_template, color="positive")

        ui.markdown("#### **Registered templates**")
        template_list_container = ui.list().classes("w-full").props("dense")
        await _inject_template_list()

    return view
