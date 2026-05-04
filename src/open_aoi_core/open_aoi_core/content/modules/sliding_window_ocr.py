# Sliding Window (Local Search) + OCR Component Inspection
# This module dynamically searches for a component within a safe margin (ROI),
# crops the exact location found, and uses OCR to read the label.

try:
    from open_aoi_core.content.modules import IModule
except ImportError:
    import sys
    sys.path.append("./src/open_aoi_core")
    from open_aoi_core.content.modules import IModule

import cv2
import numpy as np
import pytesseract
import json
from typing import List

DOCUMENTATION = """
Combines Local Sliding Window and OCR.
1. Parses EXPECTED_LABELS as a JSON dictionary to inspect multiple components.
2. Creates a "Neighborhood" (ROI) around the original zone to search.
3. Finds the component dynamically within the ROI.
4. Crops the exact location and uses Tesseract OCR to read the text.
5. Compares read text with expected label.

Required parameters:
- SLIDING_WINDOW_MATCH_THRESHOLD: float (0.0 to 1.0). Example: 0.7
- EXPECTED_LABELS: JSON string. Example: {"0": "103", "1": "102"}
- SEARCH_MARGIN: int. Pixels to look around the original zone. Example: 30
"""

class Module(IModule):
    def process(
        self,
        environment: dict,
        test_image: np.ndarray,
        template_image: np.ndarray,
        inspection_zone_list: List[IModule.InspectionZone],
    ) -> List[IModule.InspectionLog]:

        # 1. Carregar Parâmetros do Ambiente
        try:
            MATCH_THRESHOLD = float(environment.get("SLIDING_WINDOW_MATCH_THRESHOLD", 0.7))
            SEARCH_MARGIN = int(environment.get("SEARCH_MARGIN", 30))
            labels_env = environment.get("EXPECTED_LABELS", "{}")
            
            # Converte a string JSON do portal para um Dicionário Python
            expected_labels_dict = json.loads(labels_env)
        except json.JSONDecodeError:
            return [IModule.InspectionLog("ERRO: EXPECTED_LABELS não é um JSON válido. Use aspas duplas: {\"0\": \"102\"}", False)]
        except Exception as e:
            raise RuntimeError(f"Erro nos parâmetros: {str(e)}") from e

        # Converter a imagem da câmera inteira para cinza (base de busca)
        test_gray = cv2.cvtColor(test_image, cv2.COLOR_RGB2GRAY) if len(test_image.shape) == 3 else test_image
        img_h, img_w = test_gray.shape

        inspection_log_list = []

        # 2. Iterar sobre cada Zona (Box) criada no portal
        for i, zone in enumerate(inspection_zone_list):
            zone_number = i + 1
            
            # Pega o label esperado para esta zona. Se não existir no JSON, ignora a leitura de texto
            expected_label = expected_labels_dict.get(str(i), "")

            # Recortar o template perfeito da Golden Image
            target_patch_color = self.cut_inspection_zone(template_image, zone)
            if target_patch_color is None or target_patch_color.size == 0:
                inspection_log_list.append(IModule.InspectionLog(f"Zona {zone_number}: Template inválido.", False))
                continue

            target_patch_gray = cv2.cvtColor(target_patch_color, cv2.COLOR_RGB2GRAY) if len(target_patch_color.shape) == 3 else target_patch_color
            h_template, w_template = target_patch_gray.shape

            # 3. BUSCA LOCALIZADA (O "Bairro")
            # Extrair coordenadas originais da Box
            x, y = zone.stat_left, zone.stat_top
            w, h = zone.stat_width, zone.stat_height

            # Calcular os limites do "bairro" garantindo que não saiam da imagem
            search_x1 = max(0, x - SEARCH_MARGIN)
            search_y1 = max(0, y - SEARCH_MARGIN)
            search_x2 = min(img_w, x + w + SEARCH_MARGIN)
            search_y2 = min(img_h, y + h + SEARCH_MARGIN)

            # Recortar a área de busca na imagem da câmera
            roi_test_gray = test_gray[search_y1:search_y2, search_x1:search_x2]

            # Fazer o Sliding Window APENAS dentro do bairro
            result = cv2.matchTemplate(roi_test_gray, target_patch_gray, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)

            if max_val < MATCH_THRESHOLD:
                inspection_log_list.append(
                    IModule.InspectionLog(f"Zona {zone_number}: FAIL - Componente ausente ou muito torto (Score visual: {max_val:.2f})", False)
                )
                continue

            # 4. TRADUZIR COORDENADAS E RECORTAR (CROP)
            # max_loc nos dá a coordenada dentro do bairro. Precisamos somar a margem para achar na placa inteira.
            found_x = search_x1 + max_loc[0]
            found_y = search_y1 + max_loc[1]

            # Recorta exatamente o componente encontrado na imagem atual
            found_component_patch = test_gray[found_y:found_y+h_template, found_x:found_x+w_template]

            # 5. FASE DE OCR (Se houver label configurado)
            if expected_label:
                # Pré-processamento
                _, thresh = cv2.threshold(found_component_patch, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
                scaled_thresh = cv2.resize(thresh, None, fx=3.0, fy=3.0, interpolation=cv2.INTER_CUBIC)

                # Leitura
                custom_config = r'--oem 3 --psm 8'
                detected_text = pytesseract.image_to_string(scaled_thresh, config=custom_config).strip()

                # Validação (removendo espaços extras)
                clean_detected = detected_text.replace(" ", "")
                clean_expected = expected_label.replace(" ", "")

                if clean_expected and clean_expected in clean_detected:
                    log_msg = f"Zona {zone_number} (Score: {max_val:.2f}): PASS - LIDO: '{detected_text}' | ESPERADO: '{expected_label}'"
                    inspection_log_list.append(IModule.InspectionLog(log_msg, True))
                else:
                    log_msg = f"Zona {zone_number} (Score: {max_val:.2f}): FAIL OCR - Lido: '{detected_text}' | Esperado: '{expected_label}'"
                    inspection_log_list.append(IModule.InspectionLog(log_msg, False))
            else:
                # Se não tem texto esperado no JSON, aprova só pela similaridade visual (presença)
                log_msg = f"Zona {zone_number}: PASS VISUAL - Componente presente (Score: {max_val:.2f})"
                inspection_log_list.append(IModule.InspectionLog(log_msg, True))

        return inspection_log_list

module = Module()