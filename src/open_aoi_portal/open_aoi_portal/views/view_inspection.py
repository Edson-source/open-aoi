"""
    This view is used for manual inspection control. Inspection is related to camera and inspection profile. User is suppose to 
    select camera and trigger inspection. This will invoke mediator inspection service, acquire image from selected camera, 
    materialize related template and so on...
"""

import logging
import functools
from datetime import datetime
from typing import Optional, List

from PIL import Image
from nicegui import ui, app
from fastapi.responses import RedirectResponse

from open_aoi_interfaces.msg import InspectionLog
from open_aoi_core.exceptions import AuthenticationException, SystemServiceException
from open_aoi_core.controllers.camera import CameraController
from open_aoi_core.controllers.accessor import AccessorController
from open_aoi_core.controllers.inspection_target import InspectionTargetController
from open_aoi_core.models import InspectionTargetModel
from open_aoi_core.constants import MediatorServiceConstants
from open_aoi_core.services import StandardClient
from open_aoi_core.utils_ros import imgmsg_to_cv2
from open_aoi_portal.settings import ACCESS_PAGE, HOME_PAGE
from open_aoi_portal.common import (
    inject_header,
    get_session,
    get_overlay,
    to_thread,
    safe_view,
    safe_operation,
)

logger = logging.getLogger("ui.inspection_profile")


def get_view(node: StandardClient):
    @safe_view
    async def view() -> Optional[RedirectResponse]:
        session = get_session()

        accessor_controller = AccessorController(session)
        camera_controller = CameraController(session)
        inspection_target_controller = InspectionTargetController(session)

        try:
            accessor = accessor_controller.identify_session_accessor(app.storage.user)
            assert accessor.role.allow_system_view
            assert accessor.role.allow_inspection_control
        except AuthenticationException:
            return RedirectResponse(ACCESS_PAGE)
        except AssertionError:
            return RedirectResponse(HOME_PAGE)

        # Memória temporária da sessão de inspeção atual
        # 'pending' guardará a inspeção atual antes do operador confirmar
        session_data = {'logs': [], 'pending': None}

        # ------------------------------------
        # Handlers

        def _atualizar_status_sessao(e=None):
            contador = len(session_data['logs'])
            total = int(qtd_input.value) if qtd_input.value else "?"
            session_status.set_text(f"Montagens inspecionadas: {contador} / {total}")

        def _limpar_sessao():
            session_data['logs'] = []
            session_data['pending'] = None
            confirm_button.set_visibility(False)
            _atualizar_status_sessao()
            ui.notify("Sessão resetada.", type="info")

        @safe_operation
        async def _handle_inspection():
            """Handles inspection request"""
            
            if not oc_input.value:
                ui.notify("Por favor, preencha a Ordem de Compra antes de inspecionar.", type="warning")
                return

            inspection_button.disable()
            confirm_button.set_visibility(False) # Esconde o confirmar antigo durante um novo processamento
            loading_spinner.set_visibility(True)
            status_label.set_text("🤖 IA Processando... Aguarde.")
            status_label.style('color: #f2c037')

            try:
                assert camera_selection.validate()
            except AssertionError:
                ui.notify("Camera is required.", type="warning")
                inspection_button.enable()
                loading_spinner.set_visibility(False)
                status_label.set_text("")
                return

            try:
                response = await to_thread(
                    functools.partial(
                        node.await_future,
                        node.mediator_inspection(camera_selection.value),
                    )
                )
            except SystemServiceException as e:
                ui.notify(str(e), type="warning")
                inspection_button.enable()
                loading_spinner.set_visibility(False)
                status_label.set_text("❌ Falha na comunicação com o ROS2.")
                status_label.style('color: #c10015')
                return

            if response.error != MediatorServiceConstants.Error.NONE:
                ui.notify(f"Inspection failed [{response.error}]: {response.error_description}", type="negative")
                inspection_button.enable()
                loading_spinner.set_visibility(False)
                status_label.set_text("❌ Erro no processamento de imagem.")
                status_label.style('color: #c10015')
                return
            else:
                ui.notify("Análise concluída! Verifique o resultado antes de confirmar.", type="info")
                
                # --- EXTRAÇÃO DOS DADOS PARA REVISÃO EM TEMPO REAL ---
                detalhes_zonas = []
                for log_msg in response.inspection_log_list:
                    target_model = inspection_target_controller.retrieve(log_msg.id)
                    nome_zona = target_model.inspection_zone.title if target_model and target_model.inspection_zone else f"Componente ID {log_msg.id}"
                    
                    detalhes_zonas.append({
                        "nome": nome_zona,
                        "passed": log_msg.passed,
                        "motivo": log_msg.log
                    })

                # Coloca na Área de Estágio (Ainda não incrementa o lote oficial)
                session_data['pending'] = {
                    "status": "PASS" if response.overall_passed else "FAIL",
                    "timestamp": datetime.now().strftime('%H:%M:%S'),
                    "zonas": detalhes_zonas
                }

            # Atualiza imagem e overlays na tela para o operador avaliar
            image = Image.fromarray(imgmsg_to_cv2(response.image))
            image_element.set_source(image)

            overlay = ""
            for log, target in zip(response.inspection_log_list, response.inspection_target_list):
                overlay += get_overlay(target, log)
            image_element.content = overlay

            await _inject_inspection_log(response.inspection_log_list)

            # Libera o botão de inspeção e exibe o botão de confirmação humana
            inspection_button.enable()
            loading_spinner.set_visibility(False)
            confirm_button.set_visibility(True)
            status_label.set_text("⚠️ Aguardando confirmação do operador.")
            status_label.style('color: #f2c037')

        def _confirmar_montagem():
            """Grava permanentemente a inspeção pendente no lote oficial"""
            if not session_data['pending']:
                ui.notify("Nenhuma inspeção pendente para confirmar.", type="warning")
                return
            
            log_entry = session_data['pending']
            # Atribui o ID sequencial oficial apenas no momento da confirmação
            log_entry['id'] = len(session_data['logs']) + 1
            
            session_data['logs'].append(log_entry)
            session_data['pending'] = None # Limpa a área de estágio
            
            # Atualiza os componentes visuais
            confirm_button.set_visibility(False)
            status_label.set_text("✅ Montagem gravada com sucesso!")
            status_label.style('color: #21ba45')
            
            _atualizar_status_sessao()
            ui.notify(f"Montagem #{log_entry['id']} confirmada!", type="positive")

        def _gerar_relatorio():
            if not session_data['logs']:
                ui.notify("Nenhuma placa confirmada para gerar relatório.", type="warning")
                return
            
            total_esperado = int(qtd_input.value or len(session_data['logs']))
            aprovadas = sum(1 for log in session_data['logs'] if log['status'] == 'PASS')
            yield_rate = (aprovadas / total_esperado) * 100 if total_esperado > 0 else 0

            linhas_html = ""
            for log in session_data['logs']:
                cor_borda = "border-left: 6px solid #2e7d32;" if log['status'] == "PASS" else "border-left: 6px solid #c62828;"
                cor_texto = "#2e7d32" if log['status'] == "PASS" else "#c62828"
                
                zonas_html = "<table class='zone-table'><thead><tr><th>Componente</th><th>Status</th><th>Detalhe da Inspeção</th></tr></thead><tbody>"
                for z in log['zonas']:
                    z_cor = "#2e7d32" if z['passed'] else "#c62828"
                    z_status = "PASS" if z['passed'] else "FAIL"
                    zonas_html += f"<tr><td><strong>{z['nome']}</strong></td><td style='color: {z_cor}; font-weight: bold;'>{z_status}</td><td>{z['motivo']}</td></tr>"
                zonas_html += "</tbody></table>"

                linhas_html += f"""
                <details style="background: #f9f9f9; border: 1px solid #ddd; border-radius: 6px; margin-bottom: 12px; {cor_borda}">
                    <summary style="padding: 15px; font-weight: bold; cursor: pointer; display: flex; justify-content: space-between; align-items: center; list-style: none; font-size: 1.1em;">
                        <span style="flex: 1;">Montagem #{log['id']}</span>
                        <span style="flex: 1; text-align: center; color: #666; font-size: 0.9em; font-weight: normal;">Horário: {log['timestamp']}</span>
                        <span style="flex: 1; text-align: right; color: {cor_texto};">STATUS: {log['status']} ▾</span>
                    </summary>
                    <div style="padding: 15px; border-top: 1px solid #ddd; background: #fff;">
                        {zonas_html}
                    </div>
                </details>
                """

            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    @page {{ size: A4; margin: 20mm; }}
                    body {{ font-family: 'Segoe UI', sans-serif; color: #333; line-height: 1.6; background-color: white; padding: 20px; max-width: 1000px; margin: auto; }}
                    .header {{ background-color: #1a5a96; color: white; padding: 20px; border-radius: 8px; margin-bottom: 30px; }}
                    .header h1 {{ margin: 0; font-size: 22pt; }}
                    .info-grid {{ display: flex; justify-content: space-between; gap: 20px; margin-bottom: 30px; }}
                    .card {{ flex: 1; border: 1px solid #ddd; padding: 15px; border-radius: 8px; background-color: #f9f9f9; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }}
                    .stat-box {{ flex: 1; text-align: center; padding: 20px; background-color: #e3f2fd; border: 2px solid #2196f3; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }}
                    .stat-value {{ font-size: 28pt; font-weight: bold; color: #1a5a96; }}
                    table.zone-table {{ width: 100%; border-collapse: collapse; font-size: 0.9em; margin-top: 10px; }}
                    table.zone-table th {{ background-color: #f1f5f9; text-align: left; padding: 10px; border-bottom: 2px solid #cbd5e1; }}
                    table.zone-table td {{ padding: 10px; border-bottom: 1px solid #e2e8f0; }}
                    summary::-webkit-details-marker {{ display: none; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>Relatório de Qualidade - Inspeção de Lote</h1>
                    <p>Sistema AOI - Rastreabilidade de Manufatura</p>
                </div>
                <div class="info-grid">
                    <div class="card">
                        <strong>Ordem de Compra:</strong> {oc_input.value}<br>
                        <strong>Data do Lote:</strong> {datetime.now().strftime('%d/%m/%Y')}<br>
                        <strong>Placas Registradas:</strong> {len(session_data['logs'])} de {total_esperado}
                    </div>
                    <div class="stat-box">
                        <div class="stat-value">{yield_rate:.1f}%</div>
                        <strong>Aproveitamento (Yield)</strong>
                    </div>
                </div>
                <h3 style="margin-top: 40px; border-bottom: 2px solid #eee; padding-bottom: 10px;">Detalhamento das Montagens</h3>
                <div>{linhas_html}</div>
                <div style="margin-top: 50px; border-top: 1px solid #ccc; padding-top: 10px; font-size: 9pt; color: #777;">
                    Relatório gerado automaticamente pelo Open-AOI Portal - Departamento de Engenharia.
                </div>
            </body>
            </html>
            """
            
            filename = f"Relatorio_OC_{oc_input.value}_{datetime.now().strftime('%H%M')}.html"
            ui.download(html_content.encode('utf-8'), filename=filename)
            ui.notify(f"Relatório gerado! Verifique seus downloads.", type="positive")

        @safe_operation
        async def _inject_inspection_log(inspection_log_msg_list: List[InspectionLog]):
            inspection_log_container.clear()
            if len(inspection_log_msg_list):
                with inspection_log_container:
                    for log_msg in inspection_log_msg_list:
                        target: InspectionTargetModel = inspection_target_controller.retrieve(log_msg.id)
                        try:
                            assert target is not None
                        except AssertionError:
                            ui.notify("Inspection target record not found in database.", type="negative")
                            inspection_log_container.clear()
                            return

                        with ui.item():
                            with ui.item_section():
                                with ui.row():
                                    ui.markdown(f"**{target.inspection_zone.title}** | { 'accepted' if log_msg.passed else 'rejected'}. *{log_msg.log}*")
            else:
                with inspection_log_container:
                    with ui.card().classes("w-full bg-warning text-white"):
                        ui.markdown("**Inspection log is empty.**")

        # ------------------------------------

        camera_list = camera_controller.list()

        await inject_header(accessor)
        with ui.grid(columns=3).classes("w-full gap-4"):
            with ui.column().classes("col-span-1"):
                ui.markdown(f"### **Live inspection**")
                
                # --- CONTROLE DE LOTE ---
                ui.markdown(f"#### **📦 Controle de Lote (Ordem de Compra)**")
                with ui.card().classes("w-full bg-blue-50 border border-blue-200"):
                    with ui.row().classes("w-full items-center gap-2"):
                        oc_input = ui.input("OC / Lote", placeholder="Ex: 123.456").classes("flex-grow")
                        qtd_input = ui.number("Qtd. Total", value=None, format="%.0f", on_change=_atualizar_status_sessao).classes("w-24").props('placeholder="Qtd"')
                    
                    session_status = ui.label("Montagens inspecionadas: 0 / ?").classes("font-bold text-primary mt-2")
                    
                    with ui.row().classes("w-full mt-2 gap-2"):
                        ui.button("Gerar Relatório", on_click=_gerar_relatorio, icon="description").props("outline color=primary size=sm")
                        ui.button("Reset", on_click=_limpar_sessao, icon="refresh").props("flat color=negative size=sm")
                
                # --- SETUP ---
                ui.markdown(f"#### **Setup**")
                camera_selection = ui.select(
                    dict([(camera.id, camera.title) for camera in camera_list]),
                    label="Please, select camera",
                    validation={"Camera is required": lambda value: value is not None},
                ).classes("w-full")

                with ui.column().classes("w-full"):
                    with ui.row().classes("w-full"):
                        inspection_button = ui.button("Inspect", on_click=_handle_inspection, color="white").classes("w-full")
                    
                    with ui.row().classes("w-full items-center justify-center mt-2"):
                        loading_spinner = ui.spinner(size='md', color='primary')
                        loading_spinner.set_visibility(False)
                    
                    with ui.row().classes("w-full text-center justify-center"):
                        status_label = ui.label('').classes('font-bold')
                    
                    # --- NOVO BOTÃO DE CONFIRMAÇÃO ---
                    with ui.row().classes("w-full mt-2"):
                        confirm_button = ui.button(
                            "Confirmar Montagem", 
                            on_click=_confirmar_montagem, 
                            icon="check_circle"
                        ).props("color=positive").classes("w-full")
                        confirm_button.set_visibility(False) # Começa oculto

                ui.markdown(f"#### **Results**")
                inspection_log_container = ui.list().classes("w-full").props("dense")
                with inspection_log_container:
                    with ui.card().classes("w-full bg-primary text-white"):
                        ui.markdown("**No results to show.**")

            with ui.column().classes("col-span-2"):
                image_element = ui.interactive_image().classes("w-full")

    return view