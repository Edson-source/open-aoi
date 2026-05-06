import shlex
import json
from collections import defaultdict
from sqlalchemy import text

# ================= CONFIGURAÇÕES DE CALIBRAÇÃO =================
PIXELS_PER_MM = 20.0  
OFFSET_X_PX = 100     
OFFSET_Y_PX = 50      
IMAGE_HEIGHT = 1200   
HANDLER_ID = 4  # ID do seu módulo Sliding Window OCR

FOOTPRINT_MAP = {
    "0603_R_-_Reflow": (1.6, 0.8),
    "0603_C_-_REFLOW": (1.6, 0.8),
    "1206_R2_REFLOW": (3.2, 1.6),
    "0603_LED": (1.6, 0.8),
    "SOT23-8_-_REFLOW": (3.0, 3.0),
    "8SOIC_-_REFLOW": (5.0, 6.0),
    "SOD123FL_-_REFLOW": (3.5, 1.6),
}
# ===============================================================

def process_pnp_content(session, file_content: str, template_id: int, accessor_id: int, current_env: str) -> str:
    """Lê a string do arquivo P&P, injeta no DB via SQLAlchemy e retorna o novo Environment"""
    components = []
    designator_counts = defaultdict(int)
    
    # 1. Parsing do texto em memória
    lines = file_content.splitlines()
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
                
                if "TEST POINT" in comment or "PF" in comment:
                    continue
                    
                designator_counts[designator_base] += 1
                count = designator_counts[designator_base]
                designator = f"{designator_base}_{count}" if count > 1 else designator_base
                
                if count == 2:
                    for comp in components:
                        if comp['designator'] == designator_base:
                            comp['designator'] = f"{designator_base}_1"
                            
                components.append({
                    "designator": designator, "comment": comment, "footprint": footprint,
                    "x_mm": center_x_mm, "y_mm": center_y_mm, "rotation": rotation
                })
            except Exception:
                continue
                
    boxes = []
    expected_labels = {}
    
    # 2. Conversão CAD -> Pixels
    for i, comp in enumerate(components):
        x_px = int((comp['x_mm'] * PIXELS_PER_MM) + OFFSET_X_PX)
        y_px = int(IMAGE_HEIGHT - ((comp['y_mm'] * PIXELS_PER_MM) + OFFSET_Y_PX))
        
        w_mm, h_mm = FOOTPRINT_MAP.get(comp['footprint'], (2.0, 2.0))
        if comp['rotation'] in [90.0, 270.0]:
            w_mm, h_mm = h_mm, w_mm
            
        w_px = int(w_mm * PIXELS_PER_MM)
        h_px = int(h_mm * PIXELS_PER_MM)
        
        boxes.append({
            "designator": comp['designator'],
            "stat_left": x_px - (w_px // 2), "stat_top": y_px - (h_px // 2),
            "stat_width": w_px, "stat_height": h_px, "rotation": comp['rotation']
        })
        
        if comp['designator'].startswith('R') or comp['designator'].startswith('U'):
            expected_labels[str(i)] = comp['comment']
            
    # 3. Injeção no Banco usando a sessão ativa da aplicação web
    for box in boxes:
        res_zone = session.execute(text("""
            INSERT INTO InspectionZone (title, rotation, template_id, created_by_accessor_id) 
            VALUES (:title, :rot, :tpl_id, :acc_id)
        """), {"title": box['designator'], "rot": box['rotation'], "tpl_id": template_id, "acc_id": accessor_id})
        zone_id = res_zone.lastrowid
        
        session.execute(text("""
            INSERT INTO ConnectedComponent (stat_left, stat_top, stat_width, stat_height, inspection_zone_id) 
            VALUES (:l, :t, :w, :h, :z_id)
        """), {"l": box['stat_left'], "t": box['stat_top'], "w": box['stat_width'], "h": box['stat_height'], "z_id": zone_id})
        
        session.execute(text("""
            INSERT INTO InspectionTarget (inspection_zone_id, inspection_handler_id) 
            VALUES (:z_id, :h_id)
        """), {"z_id": zone_id, "h_id": HANDLER_ID})
        
    session.commit() # Salva as caixas definitivamente no banco
    
    # 4. Reconstrói o texto do JSON para retornar para a caixa da UI
    env_lines = [l for l in (current_env.split('\n') if current_env else []) if not l.startswith("EXPECTED_LABELS")]
    env_lines.append(f"EXPECTED_LABELS={json.dumps(expected_labels)}")
    
    return "\n".join(env_lines)