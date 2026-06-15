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

        # Variável de estado na memória (será populada pelo banco mais abaixo)
        fiducial_state = {'x': None, 'y': None, 'ppm': 8.5}

        # -------------------
        # Handlers
        @safe_operation
        async def _handle_create_edit_profile():
            """Function is used to create or edit inspection profile"""
            nonlocal inspection_profile  
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
                ui.navigate.to(INSPECTION_PROFILE_EDIT_PAGE.format(profile_id=inspection_profile.id))
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
            
            if fiducial_state['x'] is None or fiducial_state['y'] is None:
                ui.notify("⚠️ Clique no ponto fiducial da imagem antes de importar o P&P!", type="warning")
                e.sender.reset()
                return
            
            try:
                ui.notify(f'Processando arquivo: {e.name} com PPM {fiducial_state["ppm"]}...', type='info')
                
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
                    current_env=environment.value,
                    fiducial_x=fiducial_state['x'],
                    fiducial_y=fiducial_state['y'],
                    ppm=fiducial_state['ppm']
                )
                
                environment.set_value(new_env)
                e.sender.reset() 
                ui.notify('Engenharia injetada! Verifique as zonas na aba de Inspection Templates.', type='positive')
                
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
            # LÓGICA DE PERSISTÊNCIA (LENDO DO BANCO PARA A RAM)
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

            # Restaura os valores do banco (se existirem) ao carregar a página
            fiducial_state['ppm'] = parse_env_value('PPM', 8.5, float)
            fiducial_state['x'] = parse_env_value('FIDUCIAL_X', None, float)
            fiducial_state['y'] = parse_env_value('FIDUCIAL_Y', None, float)

            # Função centralizada para injetar os valores na string de Environment
            def update_environment(e=None):
                lines = environment.value.split('\n') if environment.value else []
                keys_to_manage = [
                    'SLIDING_WINDOW_MATCH_THRESHOLD', 
                    'SEARCH_MARGIN',
                    'OCR_CONFIDENCE',
                    'ROTATION_TOLERANCE',
                    'PPM', 'FIDUCIAL_X', 'FIDUCIAL_Y'
                ]
                
                clean_lines = [l for l in lines if not any(l.startswith(f"{k}=") for k in keys_to_manage)]
                
                # Salva os sliders visuais
                clean_lines.append(f"SLIDING_WINDOW_MATCH_THRESHOLD={visual_slider.value:.2f}")
                clean_lines.append(f"SEARCH_MARGIN={int(margin_slider.value)}")
                clean_lines.append(f"OCR_CONFIDENCE={ocr_slider.value:.2f}")
                clean_lines.append(f"ROTATION_TOLERANCE={int(rot_slider.value)}")
                
                # Salva a Calibração e Coordenadas
                clean_lines.append(f"PPM={fiducial_state['ppm']:.2f}")
                if fiducial_state['x'] is not None and fiducial_state['y'] is not None:
                    clean_lines.append(f"FIDUCIAL_X={fiducial_state['x']:.2f}")
                    clean_lines.append(f"FIDUCIAL_Y={fiducial_state['y']:.2f}")
                
                environment.set_value('\n'.join([l for l in clean_lines if l.strip()]))

            if inspection_profile is not None:
                with ui.expansion('⚙️ Tuning de Robustez da IA', icon='settings_suggest').classes('w-full border rounded-md mt-4'):
                    with ui.column().classes('w-full p-4 gap-2'):
                        
                        with ui.row().classes('w-full items-center'):
                            ui.label('Fidelidade Visual (Template):').classes('w-1/3 font-bold')
                            visual_slider = ui.slider(min=0.1, max=1.0, step=0.05, value=parse_env_value('SLIDING_WINDOW_MATCH_THRESHOLD', 0.70, float), on_change=update_environment).classes('w-1/2')
                            ui.label().bind_text_from(visual_slider, 'value', backward=lambda v: f"{v:.2f}")

                        with ui.row().classes('w-full items-center'):
                            ui.label('Margem de Busca (Folga):').classes('w-1/3 font-bold')
                            margin_slider = ui.slider(min=0, max=150, step=5, value=parse_env_value('SEARCH_MARGIN', 40, int), on_change=update_environment).classes('w-1/2')
                            ui.label().bind_text_from(margin_slider, 'value', backward=lambda v: f"{int(v)} px")

                        with ui.row().classes('w-full items-center'):
                            ui.label('Confiança do OCR (Texto):').classes('w-1/3 font-bold')
                            ocr_slider = ui.slider(min=0.1, max=1.0, step=0.05, value=parse_env_value('OCR_CONFIDENCE', 0.60, float), on_change=update_environment).classes('w-1/2')
                            ui.label().bind_text_from(ocr_slider, 'value', backward=lambda v: f"{int(v*100)}%")

                        with ui.row().classes('w-full items-center'):
                            ui.label('Tolerância de Rotação:').classes('w-1/3 font-bold')
                            rot_slider = ui.slider(min=0, max=20, step=1, value=parse_env_value('ROTATION_TOLERANCE', 5, int), on_change=update_environment).classes('w-1/2')
                            ui.label().bind_text_from(rot_slider, 'value', backward=lambda v: f"± {int(v)}°")
            
            # =========================================================================
            # CALIBRAÇÃO E IMPORTAÇÃO DO PICK & PLACE
            # =========================================================================
            if inspection_profile is not None and inspection_profile.template_id:
                ui.markdown("##### **🎯 Calibração e Importação (Pick & Place)**")
                with ui.card().classes('w-full bg-blue-50 border border-blue-200 mt-2'):
                    ui.markdown("**1. Defina o Fator de Escala (PPM).**")
                    
                    def _update_ppm(e):
                        fiducial_state['ppm'] = e.value
                        update_environment() # Guarda silenciosamente na caixa de texto

                    ppm_input = ui.number('Pixels por Milímetro (PPM) (ex.: 1920 / 300 = 6.40)', value=fiducial_state['ppm'], format='%.2f', step=0.1, on_change=_update_ppm).classes('w-48 bg-white')
                    
                    ui.markdown("**2. Clique exatamente no ponto fiducial (0,0) na imagem abaixo.**")
                    try:
                        img_data = inspection_profile.template.materialize_image()
                        
                        def on_mouse_click(e):
                            if e.type == 'click':
                                fiducial_state['x'] = e.image_x
                                fiducial_state['y'] = e.image_y
                                update_environment() # Guarda silenciosamente na caixa de texto
                                
                                mira_svg = f'''
                                    <circle cx="{e.image_x}" cy="{e.image_y}" r="15" stroke="#f2c037" stroke-width="3" fill="none" />
                                    <line x1="{e.image_x - 25}" y1="{e.image_y}" x2="{e.image_x + 25}" y2="{e.image_y}" stroke="#f2c037" stroke-width="3" />
                                    <line x1="{e.image_x}" y1="{e.image_y - 25}" x2="{e.image_x}" y2="{e.image_y + 25}" stroke="#f2c037" stroke-width="3" />
                                '''
                                interactive_img.content = mira_svg
                                ui.notify(f"🎯 Ponto Zero ancorado em X: {e.image_x:.0f}, Y: {e.image_y:.0f}. Salve o Perfil!", type="info")

                        interactive_img = ui.interactive_image(img_data, on_mouse=on_mouse_click).classes("w-full border-2 border-primary rounded-md mt-2 cursor-crosshair")
                        
                        # Se já havia um clique salvo no banco, desenha a mira na tela ao dar F5
                        if fiducial_state['x'] is not None and fiducial_state['y'] is not None:
                            interactive_img.content = f'''
                                <circle cx="{fiducial_state['x']}" cy="{fiducial_state['y']}" r="15" stroke="#f2c037" stroke-width="3" fill="none" />
                                <line x1="{fiducial_state['x'] - 25}" y1="{fiducial_state['y']}" x2="{fiducial_state['x'] + 25}" y2="{fiducial_state['y']}" stroke="#f2c037" stroke-width="3" />
                                <line x1="{fiducial_state['x']}" y1="{fiducial_state['y'] - 25}" x2="{fiducial_state['x']}" y2="{fiducial_state['y'] + 25}" stroke="#f2c037" stroke-width="3" />
                            '''

                    except Exception as e:
                        logger.error(f"Erro ao carregar imagem para fiducial: {e}")
                        ui.label("Erro ao carregar a imagem do template para calibração.").classes('text-red-500 font-bold')

                    ui.markdown("**3. Importe o arquivo P&P.**")
                    with ui.row().classes("w-full items-center"):
                        ui.add_head_html('<style>.uploader-fantasma { width: 0; height: 0; opacity: 0; position: absolute; overflow: hidden; z-index: -1; }</style>')
                        
                        ui.upload(
                            auto_upload=True,
                            max_files=1,
                            on_upload=_handle_pnp_upload,
                        ).props('accept=".txt"').classes('uploader-fantasma')

                        ui.button(
                            'Importar Pick & Place',
                            icon='upload_file',
                            on_click=lambda: ui.run_javascript("document.querySelector('.uploader-fantasma input[type=file]').click()")
                        ).props('color="primary"').classes('px-6')

            with ui.row().classes("w-full mt-4 justify-end"):
                ui.button(
                    "Save" if inspection_profile is None else "Update",
                    on_click=_handle_create_edit_profile,
                    color="positive",
                ).classes('px-6')

        ui.markdown("##### **Registered profiles**")
        profile_list_container = ui.list().classes("w-full").props("dense")
        await _inject_profile_list()

    return view