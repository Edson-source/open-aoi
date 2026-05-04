import os
import shlex
import json
from collections import defaultdict
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Carrega as variáveis do arquivo .env
load_dotenv()

# ============================================================
# 1. CONFIGURAÇÕES DO BANCO E IDS (AJUSTE AQUI)
# ============================================================
TEMPLATE_ID = 1      # ID do Template (veja na URL do navegador)
PROFILE_ID = 1       # ID do Perfil (veja na URL do navegador)
HANDLER_ID = 4       # ID do Módulo sliding_window_ocr.py
PNP_FILEPATH = r"Pick_Place.txt"

# ============================================================
# 2. CONFIGURAÇÕES DA CÂMERA (MATEMÁTICA DE PIXELS)
# ============================================================
PIXELS_PER_MM = 20.0  # Ajuste conforme a sua lente
OFFSET_X_PX = 100     # Onde o X:0 do Altium cai na sua foto
OFFSET_Y_PX = 50      # Onde o Y:0 do Altium cai na sua foto
IMAGE_HEIGHT = 1200   # Altura total da imagem capturada

# Mapa de tamanhos reais dos componentes (Largura x Altura em mm)
FOOTPRINT_MAP = {
    "0603_R_-_Reflow": (1.6, 0.8),
    "0603_C_-_REFLOW": (1.6, 0.8),
    "1206_R2_REFLOW": (3.2, 1.6),
    "0603_LED": (1.6, 0.8),
    "SOT23-8_-_REFLOW": (3.0, 3.0),
    "8SOIC_-_REFLOW": (5.0, 6.0),
    "SOD123FL_-_REFLOW": (3.5, 1.6),
}

# ============================================================
# 3. LÓGICA DE PARSER (ALTIUM -> PYTHON)
# ============================================================
def parse_pnp_file(filepath):
    components = []
    designator_counts = defaultdict(int)

    if not os.path.exists(filepath):
        print(f"❌ Erro: Arquivo {filepath} não encontrado.")
        return []

    with open(filepath, 'r') as file:
        lines = file.readlines()

    start_parsing = False
    for line in lines:
        line = line.strip()
        if not line or line.startswith("===") or line.startswith("Date"):
            continue
        if line.startswith("Designator"):
            start_parsing = True
            continue
            
        if start_parsing:
            try:
                cols = shlex.split(line)
                if len(cols) < 7: continue
                
                designator_base = cols[0]
                comment = cols[1]
                footprint = cols[3]
                center_x_mm = float(cols[4])
                center_y_mm = float(cols[5])
                rotation = float(cols[6])
                
                # Ignorar furos e fiduciários do teste de labels
                if "TEST POINT" in comment or "PF" in comment:
                    continue
                    
                # Tratamento de Painel (R1_1, R1_2...)
                designator_counts[designator_base] += 1
                count = designator_counts[designator_base]
                designator = f"{designator_base}_{count}" if count > 1 else designator_base
                
                # Retro-renomear o primeiro se achou o segundo
                if count == 2:
                    for comp in components:
                        if comp['designator'] == designator_base:
                            comp['designator'] = f"{designator_base}_1"
                            
                components.append({
                    "designator": designator,
                    "comment": comment,
                    "footprint": footprint,
                    "x_mm": center_x_mm,
                    "y_mm": center_y_mm,
                    "rotation": rotation
                })
            except Exception:
                continue
    return components

def generate_aoi_data(components):
    boxes = []
    expected_labels = {}
    
    for i, comp in enumerate(components):
        # Conversão de Coordenadas com inversão de Y
        x_px = int((comp['x_mm'] * PIXELS_PER_MM) + OFFSET_X_PX)
        y_px = int(IMAGE_HEIGHT - ((comp['y_mm'] * PIXELS_PER_MM) + OFFSET_Y_PX))
        
        # Tamanho da Box baseado no footprint
        w_mm, h_mm = FOOTPRINT_MAP.get(comp['footprint'], (2.0, 2.0))
        if comp['rotation'] in [90.0, 270.0]:
            w_mm, h_mm = h_mm, w_mm
            
        w_px = int(w_mm * PIXELS_PER_MM)
        h_px = int(h_mm * PIXELS_PER_MM)
        
        # Coordenada Top-Left (necessária para o banco)
        boxes.append({
            "designator": comp['designator'],
            "stat_left": x_px - (w_px // 2),
            "stat_top": y_px - (h_px // 2),
            "stat_width": w_px,
            "stat_height": h_px,
            "rotation": comp['rotation']
        })
        
        # Geração do Label (Somente Resistores e CIs)
        if comp['designator'].startswith('R') or comp['designator'].startswith('U'):
            expected_labels[str(i)] = comp['comment']

    return boxes, expected_labels

# ============================================================
# 4. LÓGICA DE BANCO DE DADOS (INJEÇÃO)
# ============================================================
def get_db_engine():
    return create_engine(f"mysql+pymysql://{os.getenv('MYSQL_USER')}:{os.getenv('MYSQL_PASSWORD')}@{os.getenv('MYSQL_HOST')}:{os.getenv('MYSQL_PORT')}/{os.getenv('MYSQL_DATABASE')}")

def inject_to_db(boxes, labels):
    engine = get_db_engine()
    with engine.begin() as conn:
        print(f"🔗 Conectado ao MySQL. Injetando {len(boxes)} componentes...")
        
        # Pega o ID do seu usuário Administrador automaticamente no banco
        accessor_id = conn.execute(text("SELECT id FROM Accessor LIMIT 1")).scalar()
        if not accessor_id:
            accessor_id = 1 # Fallback caso a tabela esteja vazia (improvável)
            
        for i, box in enumerate(boxes):
            # 1. Inserir a Zona (Agora com a assinatura de quem criou: created_by_accessor_id)
            res_zone = conn.execute(text("""
                INSERT INTO InspectionZone (title, rotation, template_id, created_by_accessor_id) 
                VALUES (:title, :rot, :tpl_id, :acc_id)
            """), {
                "title": box['designator'], 
                "rot": box['rotation'], 
                "tpl_id": TEMPLATE_ID,
                "acc_id": accessor_id
            })
            zone_id = res_zone.lastrowid
            
            # 2. Inserir as Coordenadas atreladas à Zona
            conn.execute(text("""
                INSERT INTO ConnectedComponent (stat_left, stat_top, stat_width, stat_height, inspection_zone_id) 
                VALUES (:l, :t, :w, :h, :z_id)
            """), {
                "l": box['stat_left'], "t": box['stat_top'], 
                "w": box['stat_width'], "h": box['stat_height'], 
                "z_id": zone_id
            })
            
            # 3. Inserir Target atrelado à Zona (Módulo de OCR)
            conn.execute(text("""
                INSERT INTO InspectionTarget (inspection_zone_id, inspection_handler_id) 
                VALUES (:z_id, :h_id)
            """), {"z_id": zone_id, "h_id": HANDLER_ID})
            
        print("✅ Tabelas de zonas populadas.")

        # 4. Atualizar Perfil (JSON) na tabela InspectionProfile
        current_env = conn.execute(text("SELECT environment FROM InspectionProfile WHERE id = :pid"), {"pid": PROFILE_ID}).scalar()
        env_lines = [l for l in (current_env.split('\n') if current_env else []) if not l.startswith("EXPECTED_LABELS")]
        env_lines.append(f"EXPECTED_LABELS={json.dumps(labels)}")
        
        conn.execute(text("UPDATE InspectionProfile SET environment = :env WHERE id = :pid"), 
                     {"env": "\n".join(env_lines), "pid": PROFILE_ID})
        print("✅ Variáveis de ambiente do Perfil atualizadas.")

if __name__ == "__main__":
    print("🚀 Iniciando processamento do Pick and Place...")
    raw_components = parse_pnp_file(PNP_FILEPATH)
    if raw_components:
        final_boxes, final_labels = generate_aoi_data(raw_components)
        inject_to_db(final_boxes, final_labels)
        print(f"\n🎉 Sucesso! {len(final_boxes)} componentes importados para o Template {TEMPLATE_ID}.")