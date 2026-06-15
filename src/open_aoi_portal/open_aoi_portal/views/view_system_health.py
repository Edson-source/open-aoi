import logging
import platform
import psutil
from datetime import datetime, timezone, timedelta
from sqlalchemy import text
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
            
            # --- CARDS DE STATUS ---
            with ui.row().classes('w-full gap-4'):
                # Card Banco de Dados
                with ui.card().classes('col-span-1 p-4 items-center w-64'):
                    db_icon = ui.icon('help').classes('text-4xl')
                    db_label = ui.label('Banco de Dados: CHECKING').classes('font-bold text-center')

                # Card Webcam Local (Browser)
                with ui.card().classes('col-span-1 p-4 items-center w-64'):
                    cam_icon = ui.icon('help').classes('text-4xl')
                    cam_label = ui.label('Webcam Local: CHECKING').classes('font-bold text-center')

                # Card Sistema Operacional (Motor Docker)
                with ui.card().classes('col-span-1 p-4 items-center w-64'):
                    cpu_icon = ui.icon('memory', color='primary').classes('text-4xl')
                    cpu_label = ui.label('CPU: --% | RAM: --%').classes('font-mono font-bold text-center')

            # --- MEMÓRIA DE ESTADO (Para evitar SPAM no Log) ---
            hardware_state = {
                'db_online': None,
                'cam_online': None
            }

            # --- O "MOTOR" DO TEMPO REAL ---
            async def update_status():
                # 1. Checa o Banco de Dados
                try:
                    session.execute(text("SELECT 1"))
                    db_icon.name = 'database'
                    db_icon.style('color: #21ba45;') # Verde
                    db_label.text = 'Banco de Dados: ONLINE'
                    db_label.style('color: #21ba45;')
                    
                    # Se mudou de estado para ONLINE, registra no log
                    if hardware_state['db_online'] is not True:
                        logger.info("Conexão com Banco de Dados estabelecida e estável.")
                        hardware_state['db_online'] = True
                except Exception as e:
                    db_icon.name = 'report_problem'
                    db_icon.style('color: #c10015;') # Vermelho
                    db_label.text = 'Banco de Dados: OFFLINE'
                    db_label.style('color: #c10015;')
                    
                    # Se mudou de estado para OFFLINE, registra no log
                    if hardware_state['db_online'] is not False:
                        logger.error("Falha na comunicação com o Banco de Dados MySQL!")
                        hardware_state['db_online'] = False

                # 2. Checa a Câmera Local
                try:
                    has_camera = await ui.run_javascript('''
                        return await navigator.mediaDevices.enumerateDevices()
                            .then(devices => devices.some(d => d.kind === "videoinput"));
                    ''', timeout=1.0)

                    if has_camera:
                        cam_icon.name = 'videocam'
                        cam_icon.style('color: #21ba45;')
                        cam_label.text = 'Webcam Local: CONNECTED'
                        cam_label.style('color: #21ba45;')
                        
                        # LOG: Câmera plugada!
                        if hardware_state['cam_online'] is not True:
                            logger.info("Hardware: Webcam Local detectada e vinculada ao sistema.")
                            hardware_state['cam_online'] = True
                    else:
                        cam_icon.name = 'videocam_off'
                        cam_icon.style('color: #c10015;')
                        cam_label.text = 'Webcam Local: DISCONNECTED'
                        cam_label.style('color: #c10015;')
                        
                        # LOG: Câmera desplutada!
                        if hardware_state['cam_online'] is not False:
                            logger.warning("Hardware: Webcam Local não encontrada (Cabo USB desconectado).")
                            hardware_state['cam_online'] = False
                except Exception:
                    cam_icon.name = 'videocam_off'
                    cam_icon.style('color: #f2c037;')
                    cam_label.text = 'Webcam: NO PERMISSION'
                    cam_label.style('color: #f2c037;')
                    
                    if hardware_state['cam_online'] is not False:
                        logger.warning("Hardware: Permissão de câmera negada pelo navegador.")
                        hardware_state['cam_online'] = False

                # 3. Checa Hardware
                cpu_label.text = f'CPU: {psutil.cpu_percent()}% | RAM: {psutil.virtual_memory().percent}%'

            # Dispara a atualização a cada 2.0 segundos
            ui.timer(2.0, update_status)

            # --- TERMINAL DE LOGS EM TEMPO REAL ---
            ui.markdown("#### 📜 Logs do Sistema (Real-time)")
            
            terminal = ui.log(max_lines=500).classes('w-full h-96 bg-black text-green-400 font-mono text-xs p-2 border-4 border-gray-800')
            
            class WebTerminalHandler(logging.Handler):
                def emit(self, record):
                    try:
                        msg = record.getMessage() 
                        tz_br = timezone(timedelta(hours=-3))
                        hora_local = datetime.now(tz_br).strftime('%H:%M:%S')
                        terminal.push(f"[{hora_local}] [{record.levelname}] {msg}")
                    except:
                        pass

            web_handler = WebTerminalHandler()
            
            # Lista exata dos canais que queremos monitorar (Sem o root_logger para evitar eco)
            canais_de_log = ["ui.system_health", "uvicorn.access", "uvicorn.error", "nicegui"]
            
            for nome_canal in canais_de_log:
                canal = logging.getLogger(nome_canal)
                
                # O Pulo do Gato: Varre e destrói handlers antigos antes de adicionar o novo
                # Isso mata os "fantasmas" gerados ao dar F5 ou trocar de página
                canal.handlers = [h for h in canal.handlers if not isinstance(h, WebTerminalHandler)]
                
                canal.addHandler(web_handler)
                canal.setLevel(logging.INFO)
            
            with ui.row().classes('w-full mt-2'):
                ui.button('Limpar Terminal', on_click=terminal.clear, icon='delete').props('outline size=sm')
                ui.button('Gerar Log de Teste', on_click=lambda: logger.info("Sistema de escuta de rede operando limpo e sem eco!")).props('outline size=sm color=secondary')
    return view