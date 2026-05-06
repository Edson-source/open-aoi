"""
    This view works with inspection profiles and is used to create, delete and edit them.
"""

import logging
from typing import Optional
from functools import partial

from nicegui import ui, app
from fastapi.responses import RedirectResponse

from open_aoi_core.constants import SystemLimit
from open_aoi_core.models import InspectionProfileModel
from open_aoi_core.services import StandardClient
from open_aoi_core.exceptions import AuthenticationException, SystemIntegrityException
from open_aoi_core.controllers.accessor import AccessorController
from open_aoi_core.controllers.template import TemplateController
from open_aoi_core.controllers.inspection_profile import InspectionProfileController
from open_aoi_portal.settings import (
    ACCESS_PAGE,
    HOME_PAGE,
    INSPECTION_PROFILE_EDIT_PAGE,
    INSPECTION_PROFILE_CREATE_PAGE,
)
from open_aoi_portal.common import (
    inject_text_field,
    inject_header,
    get_session,
    confirm,
    safe_view,
    safe_operation,
)

logger = logging.getLogger("ui.inspection_profile")


def get_view(node: StandardClient):
    @safe_view
    async def view(profile_id: Optional[int] = None) -> Optional[RedirectResponse]:
        session = get_session()
        accessor_controller = AccessorController(session)
        template_controller = TemplateController(session)
        inspection_profile_controller = InspectionProfileController(session)

        try:
            accessor = accessor_controller.identify_session_accessor(app.storage.user)
            assert accessor.role.allow_system_view
            assert accessor.role.allow_system_operations
        except AuthenticationException:
            return RedirectResponse(ACCESS_PAGE)
        except AssertionError:
            return RedirectResponse(HOME_PAGE)

        # -------------------
        # Handlers
        @safe_operation
        async def _handle_create_edit_profile():
            """Function is used to create or edit inspection profile"""
            nonlocal inspection_profile  # For editing profile will be initiated externally
            try:
                assert profile_title.validate()
                assert profile_description.validate()
                assert environment.validate()
                assert identification_code.validate()
                assert template_select.validate()
            except AssertionError:
                ui.notify("Some required parameters are missing", type="warning")
                return

            try:
                template = template_controller.retrieve(template_select.value)
                assert template is not None
            except AssertionError as e:
                logger.exception(e)
                ui.notify("Failed to retrieve data from database.", type="negative")
                return

            title_value = profile_title.value.strip()
            description_value = profile_description.value.strip()
            identification_code_value = identification_code.value.strip()
            environment_value = environment.value.strip()

            if inspection_profile is None:
                inspection_profile = inspection_profile_controller.create(
                    title=title_value,
                    description=description_value,
                    identification_code=identification_code_value,
                    environment=environment_value,
                    template=template,
                    accessor=accessor,
                )
                inspection_profile_controller.commit()
                ui.notify("New profile created", type="positive")
            else:
                inspection_profile.environment = environment_value
                inspection_profile_controller.commit()
                ui.notify("Updated", type="positive")
            await _inject_profile_list()

        @safe_operation
        async def _handle_pnp_upload(e):
            """Process the Pick & Place .txt file and inject zones automatically"""
            if inspection_profile is None:
                ui.notify("Por favor, salve o perfil primeiro antes de importar a engenharia.", type="warning")
                return
            
            try:
                ui.notify(f'Processando arquivo: {e.name}...', type='info')
                
                raw_bytes = e.content.read()
                try:
                    content = raw_bytes.decode('utf-8')
                except UnicodeDecodeError:
                    content = raw_bytes.decode('latin-1')

                template_id = template_select.value
                
                if not template_id:
                    ui.notify("Selecione um Template antes de importar.", type="warning")
                    return

                from open_aoi_core.utils_pnp import process_pnp_content
                
                new_env = process_pnp_content(
                    session=session,
                    file_content=content,
                    template_id=template_id,
                    accessor_id=accessor.id,
                    current_env=environment.value
                )
                
                environment.set_value(new_env)
                
                # --- NOVO: Limpa o componente de upload ---
                e.sender.reset() 
                
                ui.notify('Engenharia injetada! Clique em Update para salvar o Environment.', type='positive')
                
            except Exception as ex:
                logger.exception(ex)
                ui.notify(f"Erro ao processar: {str(ex)}", type="negative")
                
        @safe_operation
        async def _handle_delete_profile(profile: InspectionProfileModel):
            """Handles delete operation with confirmation"""

            @safe_operation
            async def _delete():
                try:
                    inspection_profile_controller.delete(profile)
                    inspection_profile_controller.commit()
                except SystemIntegrityException as e:
                    logger.exception(e)
                    ui.notify(str(e), type="warning")
                    return

                ui.notify("Profile deleted", type="positive")
                if (
                    inspection_profile is not None
                    and profile.id == inspection_profile.id
                ):
                    ui.navigate.to(INSPECTION_PROFILE_CREATE_PAGE)
                    return
                await _inject_profile_list()

            confirm(
                f"You are about to delete inspection profile {profile.title} ({profile.identification_code}). Are you sure?",
                _delete,
            )

        @safe_operation
        async def _handle_edit_profile(profile: InspectionProfileModel):
            """Redirect to profile page for editing"""
            ui.navigate.to(INSPECTION_PROFILE_EDIT_PAGE.format(profile_id=profile.id))

        @safe_operation
        async def _handle_activate_profile(profile: InspectionProfileModel):
            """Mark profile as active"""
            try:
                inspection_profile_controller.activate(profile)
                inspection_profile_controller.commit()
            except SystemIntegrityException as e:
                logger.exception(e)
                ui.notify(str(e), type="negative")
                return

            await _inject_profile_list()

        @safe_operation
        async def _handle_deactivate_profile(profile: InspectionProfileModel):
            """Mark profile as inactive"""
            try:
                inspection_profile_controller.deactivate(profile)
                inspection_profile_controller.commit()
            except SystemIntegrityException as e:
                logger.exception(e)
                ui.notify(str(e), type="negative")
                return

            await _inject_profile_list()

        # Local injections
        @safe_operation
        async def _inject_profile_list():
            """Generate list of available profiles"""
            profile_list_container.clear()
            profile_list = inspection_profile_controller.list_nested()

            with profile_list_container:
                if len(profile_list):
                    for profile in profile_list:
                        with ui.item(
                            f"{profile.title} ({profile.template.title}, code: {profile.identification_code}). {profile.description}"
                        ).props("clickable"):
                            ui.tooltip(profile.environment or "<<Empty environment>>")
                            with ui.item_section():
                                with ui.row():
                                    ui.space()
                                    ui.button(
                                        (
                                            "Deactivate"
                                            if profile.is_active
                                            else "Activate"
                                        ),
                                        color="warning" if profile.is_active else None,
                                        on_click=(
                                            partial(_handle_deactivate_profile, profile)
                                            if profile.is_active
                                            else partial(
                                                _handle_activate_profile, profile
                                            )
                                        ),
                                    ).props("size=sm")
                                    ui.button(
                                        "Edit",
                                        color="white",
                                        on_click=partial(_handle_edit_profile, profile),
                                    ).props("size=sm")
                                    ui.button(
                                        "Remove",
                                        on_click=partial(
                                            _handle_delete_profile, profile
                                        ),
                                        color="negative",
                                    ).props("size=sm")
                else:
                    with ui.card().classes("w-full bg-primary text-white"):
                        ui.markdown("**No profiles to show.**")

        # -------------------

        await inject_header(accessor)

        try:
            if profile_id is None:
                inspection_profile = None
            else:
                inspection_profile = inspection_profile_controller.retrieve(profile_id)
            template_list = dict(
                [
                    (template.id, template.title)
                    for template in template_controller.list()
                ]
            )
        except Exception as e:
            logger.exception(e)
            return RedirectResponse(INSPECTION_PROFILE_CREATE_PAGE)

        with ui.column().classes("w-full"):
            ui.markdown("#### **Inspection profile**")
            ui.markdown(
                (
                    "Inspection profile is a way to connect product with template and so with inspection algorithms. "
                    "When product image is captured for test it will be identified with barcode and inspection profile will be looked up (if active). "
                    "After inspection profile is found, template image will be retrieved and inspection conducted according to template's inspection zones. "
                    "If any inspection module require parameters, they should be defined in inspection profile environment field as string in form: PARAMETER=VALUE (one parameter per line)."
                )
            )
            ui.markdown("##### **Create profile**")
            profile_title = await inject_text_field(
                "Profile title", "Enter profile title...", SystemLimit.TITLE_LENGTH
            )
            profile_title.set_enabled(inspection_profile is None)
            if inspection_profile is not None:
                profile_title.set_value(inspection_profile.title)

            profile_description = await inject_text_field(
                "Profile description",
                "Enter profile description...",
                SystemLimit.DESCRIPTION_LENGTH,
            )
            profile_description.set_enabled(inspection_profile is None)
            if inspection_profile is not None:
                profile_description.set_value(inspection_profile.description)

            identification_code = await inject_text_field(
                "Product identification code (0000 RX.X)",
                "Enter product code identification...",
                SystemLimit.IDENTIFICATION_CODE_LENGTH,
            )
            identification_code.set_enabled(inspection_profile is None)
            if inspection_profile is not None:
                identification_code.set_value(inspection_profile.identification_code)

            template_select = ui.select(
                template_list,
                label="Template",
                clearable=True,
                validation={"Template is required": lambda value: value is not None},
            ).classes("w-full")
            template_select.set_enabled(inspection_profile is None)
            if inspection_profile is not None:
                template_select.set_value(inspection_profile.template_id)

            environment = ui.textarea(
                "Environment",
                placeholder="Enter environmental variables for used algorithms.",
            ).classes("w-full")
            if inspection_profile is not None:
                environment.set_value(inspection_profile.environment)

            # =========================================================================
            # INÍCIO DO BLOCO DE TUNING VISUAL (OPÇÃO 2)
            # =========================================================================
            def parse_env_value(key, default, cast_type):
                if environment.value:
                    for line in environment.value.split('\n'):
                        if line.startswith(f"{key}="):
                            try:
                                return cast_type(line.split('=')[1])
                            except:
                                pass
                return default

            def update_environment(e=None):
                lines = environment.value.split('\n') if environment.value else []
                keys_to_manage = [
                    'SLIDING_WINDOW_MATCH_THRESHOLD', 
                    'SEARCH_MARGIN',
                    'OCR_CONFIDENCE',
                    'ROTATION_TOLERANCE'
                ]
                
                clean_lines = [l for l in lines if not any(l.startswith(f"{k}=") for k in keys_to_manage)]
                
                clean_lines.append(f"SLIDING_WINDOW_MATCH_THRESHOLD={visual_slider.value:.2f}")
                clean_lines.append(f"SEARCH_MARGIN={int(margin_slider.value)}")
                clean_lines.append(f"OCR_CONFIDENCE={ocr_slider.value:.2f}")
                clean_lines.append(f"ROTATION_TOLERANCE={int(rot_slider.value)}")
                
                environment.set_value('\n'.join([l for l in clean_lines if l.strip()]))

            if inspection_profile is not None:
                with ui.expansion('⚙️ Tuning de Robustez da IA', icon='settings_suggest').classes('w-full border rounded-md mt-4'):
                    with ui.column().classes('w-full p-4 gap-2'):
                        
                        # 1. Match Visual (Sensibilidade de detecção)
                        with ui.row().classes('w-full items-center'):
                            ui.label('Fidelidade Visual (Template):').classes('w-1/3 font-bold')
                            visual_slider = ui.slider(min=0.1, max=1.0, step=0.05, value=parse_env_value('SLIDING_WINDOW_MATCH_THRESHOLD', 0.70, float), on_change=update_environment).classes('w-1/2')
                            ui.label().bind_text_from(visual_slider, 'value', backward=lambda v: f"{v:.2f}")

                        # 2. Margem de Busca (Folga mecânica)
                        with ui.row().classes('w-full items-center'):
                            ui.label('Margem de Busca (Folga):').classes('w-1/3 font-bold')
                            margin_slider = ui.slider(min=0, max=150, step=5, value=parse_env_value('SEARCH_MARGIN', 40, int), on_change=update_environment).classes('w-1/2')
                            ui.label().bind_text_from(margin_slider, 'value', backward=lambda v: f"{int(v)} px")

                        # 3. OCR Confidence (Rigidez da leitura)
                        with ui.row().classes('w-full items-center'):
                            ui.label('Confiança do OCR (Texto):').classes('w-1/3 font-bold')
                            ocr_slider = ui.slider(min=0.1, max=1.0, step=0.05, value=parse_env_value('OCR_CONFIDENCE', 0.60, float), on_change=update_environment).classes('w-1/2')
                            ui.label().bind_text_from(ocr_slider, 'value', backward=lambda v: f"{int(v*100)}%")

                        # 4. Tolerância de Rotação (Giro da placa)
                        with ui.row().classes('w-full items-center'):
                            ui.label('Tolerância de Rotação:').classes('w-1/3 font-bold')
                            rot_slider = ui.slider(min=0, max=20, step=1, value=parse_env_value('ROTATION_TOLERANCE', 5, int), on_change=update_environment).classes('w-1/2')
                            ui.label().bind_text_from(rot_slider, 'value', backward=lambda v: f"± {int(v)}°")
            # =========================================================================
            # FIM DO BLOCO DE TUNING VISUAL
            # =========================================================================
            
            # --- AQUI ESTÁ A MUDANÇA NA UI (Padrão Botão Nativo) ---
            with ui.row().classes("w-full items-center gap-4"):
                ui.space()
                
                if inspection_profile is not None:
                    # 1. Classe CSS para deixar o uploader "fantasma" na tela
                    ui.add_head_html('<style>.uploader-fantasma { width: 0; height: 0; opacity: 0; position: absolute; overflow: hidden; z-index: -1; }</style>')
                    
                    # 2. O Uploader Invisível
                    ui.upload(
                        auto_upload=True,
                        max_files=1,
                        on_upload=_handle_pnp_upload,
                    ).props('accept=".txt"').classes('uploader-fantasma')

                    # 3. O Botão Real e Amigável!
                    # O "run_javascript" procura o input de arquivo escondido e clica nele!
                    ui.button(
                        'Importar P&P',
                        icon='upload_file',
                        on_click=lambda: ui.run_javascript("document.querySelector('.uploader-fantasma input[type=file]').click()")
                    ).props('color="primary"').classes('px-6')

                ui.button(
                    "Save" if inspection_profile is None else "Update",
                    on_click=_handle_create_edit_profile,
                    color="positive",
                ).classes('px-6')

        ui.markdown("##### **Registered profiles**")
        profile_list_container = ui.list().classes("w-full").props("dense")
        await _inject_profile_list()

    return view