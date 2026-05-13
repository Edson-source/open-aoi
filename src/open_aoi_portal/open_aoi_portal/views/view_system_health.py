import logging
import platform
import psutil
import requests
from datetime import datetime, timezone, timedelta
from sqlalchemy import text # IMPORTANTE: Importação necessária para o banco
from nicegui import ui, app
from open_aoi_core.controllers.accessor import AccessorController
from open_aoi_portal.common import inject_header, get_session, safe_view

logger = logging.getLogger("ui.system_health")

def get_view(node):
    @safe_view
    async def view():
        session = get_session()
        accessor_controller = AccessorController(session)
        
        accessor = accessor_controller.identify_session_accessor(app.storage.user)
        await inject_header(accessor)

        with ui.column().classes('w-full p-4 gap-4'):
            ui.markdown("### 🖥️ Central de Comando e Diagnóstico")
            
            # --- CARDS DE STATUS (Elementos vazios que serão preenchidos pelo Timer) ---
            with ui.row().classes('w-full gap-4'):
                # Card Banco de Dados
                with ui.card().classes('col-span-1 p-4 items-center w-64'):
                    db_icon = ui.icon('help').classes('text-4xl')
                    db_label = ui.label('Banco de Dados: CHECKING').classes('font-bold')

                # Card Camera Server
                with ui.card().classes('col-span-1 p-4 items-center w-64'):
                    cam_icon = ui.icon('help').classes('text-4xl')
                    cam_label = ui.label('Camera Server: CHECKING').classes('font-bold')

                # Card Sistema Operacional
                with ui.card().classes('col-span-1 p-4 items-center w-64'):
                    cpu_icon = ui.icon('memory', color='primary').classes('text-4xl')
                    cpu_label = ui.label('CPU: --% | RAM: --%').classes('font-mono font-bold')

            # --- O "MOTOR" DO TEMPO REAL ---
            def update_status():
                # 1. Checa o Banco de Dados (usando text() do SQLAlchemy)
                try:
                    session.execute(text("SELECT 1"))
                    db_icon.name = 'database'
                    db_icon.style('color: #21ba45;') # Verde
                    db_label.text = 'Banco de Dados: ONLINE'
                    db_label.style('color: #21ba45;')
                except Exception as e:
                    db_icon.name = 'report_problem'
                    db_icon.style('color: #c10015;') # Vermelho
                    db_label.text = 'Banco de Dados: OFFLINE'
                    db_label.style('color: #c10015;')

                # 2. Checa a Câmera (Flask)
                try:
                    # Timeout de 0.5s para não travar a tela se estiver offline
                    requests.get("http://localhost:5000/status", timeout=0.5) 
                    cam_icon.name = 'videocam'
                    cam_icon.style('color: #21ba45;')
                    cam_label.text = 'Camera Server: ONLINE'
                    cam_label.style('color: #21ba45;')
                except:
                    cam_icon.name = 'videocam_off'
                    cam_icon.style('color: #c10015;')
                    cam_label.text = 'Camera Server: DISCONNECTED'
                    cam_label.style('color: #c10015;')

                # 3. Checa Hardware
                cpu_label.text = f'CPU: {psutil.cpu_percent()}% | RAM: {psutil.virtual_memory().percent}%'

            # Dispara a atualização a cada 2.0 segundos
            ui.timer(2.0, update_status)

            # --- TERMINAL DE LOGS EM TEMPO REAL ---
            ui.markdown("#### 📜 Logs do Sistema (Real-time)")
            
            terminal = ui.log(max_lines=500).classes('w-full h-96 bg-black text-green-400 font-mono text-xs p-2 border-4 border-gray-800')
            
            # Handler customizado para jogar os logs na tela com UTC-3
            class WebTerminalHandler(logging.Handler):
                def emit(self, record):
                    try:
                        # Pega apenas a mensagem limpa
                        msg = record.getMessage() 
                        
                        # Aplica o Fuso Horário de Brasília (UTC-3)
                        tz_br = timezone(timedelta(hours=-3))
                        hora_local = datetime.now(tz_br).strftime('%H:%M:%S')
                        
                        # Formata a string com o nível do log (INFO, WARNING)
                        terminal.push(f"[{hora_local}] [{record.levelname}] {msg}")
                    except:
                        pass

            root_logger = logging.getLogger()
            
            # Evita duplicar handlers se você der F5 na página
            if not any(isinstance(h, WebTerminalHandler) for h in root_logger.handlers):
                web_handler = WebTerminalHandler()
                
                # 1. Prende no Log Raiz
                root_logger.addHandler(web_handler)
                root_logger.setLevel(logging.INFO)
                
                # 2. GRAMPO: Prende nos logs "escondidos" do Servidor Web (Uvicorn) e NiceGUI
                # Isso vai capturar todos os cliques, salvamentos no banco e tráfego web
                for logger_name in ["uvicorn.access", "uvicorn.error", "nicegui"]:
                    specific_logger = logging.getLogger(logger_name)
                    specific_logger.addHandler(web_handler)
                    specific_logger.setLevel(logging.INFO)
            
            with ui.row().classes('w-full mt-2'):
                ui.button('Limpar Terminal', on_click=terminal.clear, icon='delete').props('outline size=sm')
                ui.button('Gerar Log de Teste', on_click=lambda: logging.info("Sistema de escuta de rede e fuso horário operacionais!")).props('outline size=sm color=secondary')

    return view

    return view