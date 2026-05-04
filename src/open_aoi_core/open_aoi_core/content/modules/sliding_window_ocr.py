# Sliding Window + OCR Component Inspection
# This module dynamically searches for a component using template matching,
# crops the found region, and uses OCR to read the label on the component.

try:
    from open_aoi_core.content.modules import IModule
except ImportError:
    import sys
    sys.path.append("./src/open_aoi_core")
    from open_aoi_core.content.modules import IModule

import cv2
import numpy as np
import pytesseract
from typing import List

DOCUMENTATION = """
Combines Sliding Window and OCR.
1. Finds the component dynamically (ignores slight board shifts).
2. Crops the exact location found on the test image.
3. Reads the text on the component using Tesseract OCR.
4. Compares read text with expected label.

Required parameters:
- SLIDING_WINDOW_MATCH_THRESHOLD: float (0.0 to 1.0). Example: 0.8
- EXPECTED_LABEL: string. The text expected on the component. Example: "103"
"""

class Module(IModule):
    def process(
        self,
        environment: dict,
        test_image: np.ndarray,
        template_image: np.ndarray,
        inspection_zone_list: List[IModule.InspectionZone],
    ) -> List[IModule.InspectionLog]:

        try:
            MATCH_THRESHOLD = float(environment.get("SLIDING_WINDOW_MATCH_THRESHOLD", 0.8))
            # Nova variável: O texto que DEVERIA estar escrito no componente
            EXPECTED_LABEL = environment.get("EXPECTED_LABEL", "")
        except Exception as e:
            raise RuntimeError("Parameters are missing or malformed.") from e

        if not EXPECTED_LABEL:
            return [IModule.InspectionLog("ERRO: EXPECTED_LABEL não configurado no ambiente.", False)]

        # Converter para escala de cinza para o Template Matching
        test_gray = cv2.cvtColor(test_image, cv2.COLOR_RGB2GRAY) if len(test_image.shape) == 3 else test_image

        inspection_log_list = []

        for zone in inspection_zone_list:
            zone_number = inspection_zone_list.index(zone) + 1
            
            # 1. FASE DE BUSCA: Recorta o template perfeito (original)
            target_patch_color = self.cut_inspection_zone(template_image, zone)
            
            if target_patch_color is None or target_patch_color.size == 0:
                inspection_log_list.append(IModule.InspectionLog(f"Zona {zone_number}: Template inválido.", False))
                continue

            target_patch_gray = cv2.cvtColor(target_patch_color, cv2.COLOR_RGB2GRAY) if len(target_patch_color.shape) == 3 else target_patch_color
            h_template, w_template = target_patch_gray.shape

            # Procurar na imagem da câmera (Test Image)
            result = cv2.matchTemplate(test_gray, target_patch_gray, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)

            # Se a similaridade visual for muito baixa, o componente nem sequer está lá (ou está muito torto)
            if max_val < MATCH_THRESHOLD:
                inspection_log_list.append(
                    IModule.InspectionLog(f"Zona {zone_number}: FALHA Visual - Componente não encontrado (Score: {max_val:.2f})", False)
                )
                continue

            # 2. FASE DE RECORTE (CROP):
            # Usamos as coordenadas exatas onde o componente foi encontrado (max_loc) 
            # para recortar A IMAGEM DA CÂMERA, não o template!
            start_x, start_y = max_loc[0], max_loc[1]
            found_component_patch = test_gray[start_y:start_y+h_template, start_x:start_x+w_template]

            # 3. FASE DE OCR (LEITURA):
            # Pré-processamento para ajudar o Tesseract (Binarização / Otsu)
            _, thresh = cv2.threshold(found_component_patch, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
            
            # Ampliar a imagem geralmente ajuda o Tesseract a ler letras minúsculas de SMD
            scaled_thresh = cv2.resize(thresh, None, fx=3.0, fy=3.0, interpolation=cv2.INTER_CUBIC)

            # Executar Tesseract
            # --psm 8: Diz ao Tesseract para assumir que a imagem é apenas UMA PALAVRA (ideal para SMD)
            custom_config = r'--oem 3 --psm 8'
            detected_text = pytesseract.image_to_string(scaled_thresh, config=custom_config).strip()

            # 4. FASE DE VALIDAÇÃO
            # Vamos limpar o texto tirando espaços em branco no meio caso o OCR leia "1 0 3"
            clean_detected = detected_text.replace(" ", "")
            clean_expected = EXPECTED_LABEL.replace(" ", "")

            if clean_expected in clean_detected:
                log_msg = f"Zona {zone_number}: PASS - Encontrado em ({start_x}, {start_y}). LIDO: '{detected_text}' | ESPERADO: '{EXPECTED_LABEL}'"
                inspection_log_list.append(IModule.InspectionLog(log_msg, True))
            else:
                log_msg = f"Zona {zone_number}: FAIL - COMPONENTE ERRADO. Lido: '{detected_text}' | Esperado: '{EXPECTED_LABEL}'"
                inspection_log_list.append(IModule.InspectionLog(log_msg, False))

        return inspection_log_list

module = Module()