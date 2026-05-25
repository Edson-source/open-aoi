"""
    This view allow to create a template by capturing an image. List of templates is also available.
"""

import logging
import base64
import io
from functools import partial
from typing import Optional

from PIL import Image
from nicegui import ui, app
from fastapi.responses import RedirectResponse

from open_aoi_core.constants import SystemLimit
from open_aoi_core.services import StandardClient
from open_aoi_core.models import TemplateModel
from open_aoi_core.controllers.template import TemplateController
from open_aoi_core.controllers.accessor import AccessorController
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
            
            _handle_retake_image()
            template_title.set_value("")
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
            """Capture image for template using browser webcam via JS"""
            nonlocal template_image

            capture_image.disable()
            try:
                # Dispara a função JS que está na nossa injeção HTML
                base64_str = await ui.run_javascript('window.captureWebcamImage()', timeout=5.0)
                
                if not base64_str:
                    raise ValueError("A captura de vídeo retornou vazia. A câmera está ligada?")
                
                # O JS devolve uma string tipo 'data:image/jpeg;base64,/9j/4AAQSkZJ...'
                # Precisamos arrancar o cabeçalho e decodificar a imagem
                img_data = base64.b64decode(base64_str.split(',')[1])
                pil_image = Image.open(io.BytesIO(img_data))
                
                template_image = pil_image
                template_image_element.set_source(template_image)
                
                camera_ui.set_visibility(False)
                template_image_element.set_visibility(True)
                btn_retake.set_visibility(True)
                
                ui.notify("Golden Image capturada! Preencha o título e clique em Save.", type="positive")
            except Exception as e:
                logger.error(f"Erro ao capturar template: {e}")
                ui.notify("Falha ao acessar a câmera. O navegador bloqueou o acesso?", type="negative")
            finally:
                capture_image.enable()

        def _handle_retake_image():
            """Descarta a foto atual e reabre a câmera"""
            nonlocal template_image
            template_image = None
            template_image_element.set_source(None)
            
            template_image_element.set_visibility(False)
            btn_retake.set_visibility(False)
            camera_ui.set_visibility(True)

        # Local injections
        @safe_operation
        async def _inject_template_list():
            """Generate list of available templates"""
            template_list_container.clear()
            template_list = template_controller.list_nested()

            with template_list_container:
                if len(template_list):
                    for template in template_list:
                        partial_preview = partial(_handle_preview_template, template)
                        partial_delete = partial(_handle_delete_template, template)
                        partial_edit = partial(
                            ui.navigate.to, CONTROL_ZONE_PAGE.format(template_id=template.id)
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

        with ui.column().classes("w-full"):
            ui.markdown("### **Templates**")
            ui.markdown(
                (
                    "Template is a golden image of a product. Template image will be captured directly from your web browser. "
                    "After capturing template image inspection zone editor will be available. "
                )
            )
            ui.markdown("#### **Template configuration**")
            template_title = await inject_text_field(
                "Template title", "Enter title value...", SystemLimit.TITLE_LENGTH
            )

            template_image = None
            
            with ui.row().classes("justify-center w-full"):
                
                # 1. A Estrutura Visual (HTML puro, sem script)
                camera_ui = ui.html('''
                    <div style="width: 100%; display: flex; justify-content: center;">
                        <video id="webcam" autoplay playsinline style="width: 100%; max-width: 600px; border: 2px solid #ccc; border-radius: 8px;"></video>
                        <canvas id="webcam-canvas" style="display:none;"></canvas>
                    </div>
                ''').classes("w-full flex justify-center")
                
                # 2. A Lógica de Captura (JavaScript seguro no Body)
                ui.add_body_html('''
                    <script>
                        setTimeout(() => {
                            const video = document.getElementById('webcam');
                            if (video && navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
                                navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment", width: { ideal: 1920 } } })
                                    .then(stream => { video.srcObject = stream; })
                                    .catch(err => { console.error("Erro na webcam:", err); });
                            }
                        }, 500);

                        window.captureWebcamImage = function() {
                            const video = document.getElementById('webcam');
                            const canvas = document.getElementById('webcam-canvas');
                            if (!video || !video.videoWidth) return null;
                            canvas.width = video.videoWidth;
                            canvas.height = video.videoHeight;
                            canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
                            return canvas.toDataURL('image/jpeg', 0.9);
                        };
                    </script>
                ''')
                
                # Imagem capturada (começa oculta)
                template_image_element = ui.interactive_image().classes("w-full max-w-2xl border-2 border-primary rounded")
                template_image_element.set_visibility(False)

            with ui.row().classes("w-full mt-4"):
                ui.space()
                
                btn_retake = ui.button("Refazer Foto", on_click=_handle_retake_image, icon="refresh").props("outline color=warning")
                btn_retake.set_visibility(False)
                
                capture_image = ui.button(
                    "Capture Golden Image",
                    on_click=_handle_capture_image,
                    icon="photo_camera",
                    color="primary",
                )
                ui.button("Save Template", on_click=_handle_create_template, color="positive")

        ui.markdown("#### **Registered templates**")
        template_list_container = ui.list().classes("w-full").props("dense")
        await _inject_template_list()

    return view