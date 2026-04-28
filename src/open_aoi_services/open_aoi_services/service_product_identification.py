import rclpy
import cv2 as cv
import numpy as np

from open_aoi_interfaces.srv import IdentificationTrigger
from open_aoi_core.services import StandardService
from open_aoi_core.utils_basic import isolate_product, Profiler
from open_aoi_core.utils_ros import imgmsg_to_cv2
from open_aoi_core.constants import ProductIdentificationConstants, SystemServiceStatus

class Service(StandardService):
    NODE_NAME = ProductIdentificationConstants.NODE_NAME

    def __init__(self):
        super().__init__()
        self.registration_service = self.create_service(
            IdentificationTrigger,
            f"{self.NODE_NAME}/get_barcode",
            self.get_barcode,
        )
        self.barcode_detector = cv.barcode.BarcodeDetector()
        self.qrcode_detector = cv.QRCodeDetector()

    def apply_smart_sharpening(self, image):
        """Aplica nitidez e contraste. Requer imagem colorida (RGB) na entrada."""
        # 1. Converter para cinza (O CLAHE e o Unsharp Mask exigem tons de cinza)
        gray = cv.cvtColor(image, cv.COLOR_RGB2GRAY)

        # 2. Unsharp Masking
        blurred = cv.GaussianBlur(gray, (0, 0), sigmaX=2.0)
        sharpened = cv.addWeighted(gray, 1.6, blurred, -0.6, 0)

        # 3. CLAHE (Contrast Limited Adaptive Histogram Equalization)
        clahe = cv.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
        enhanced = clahe.apply(sharpened)

        return enhanced

    def preprocess_image(self, image):
        """Aplica filtros para facilitar a leitura do código."""
        # A imagem chega aqui em RGB (já corrigida no serviço de aquisição).
        # Aplicamos a nitidez inteligente, que já devolve a imagem tratada em escala de cinza.
        processed_gray = self.apply_smart_sharpening(image)
        return processed_gray

    def get_barcode(self, request, response):
        p = Profiler()
        self.logger.info(f"Iniciando inspeção de ID. [{p.tick()}]")
        self.set_status(SystemServiceStatus.BUSY)

        identification_code = ""
        try:
            # Converte imagem do ROS (Ela entra aqui em formato RGB)
            raw_image = imgmsg_to_cv2(request.image)
            
            # Pré-processamento
            processed_img = self.preprocess_image(raw_image)
            self.logger.info(f"Pré-processamento concluído. [{p.tick()}]")

            # Tenta detecção de Código de Barras (Desempacotamento flexível para evitar erros)
            res_bar = self.barcode_detector.detectAndDecode(processed_img)
            
            # res_bar geralmente retorna (ok, decoded_info, pontos, ...)
            if res_bar and res_bar[0]: 
                # Dependendo do OpenCV, decoded_info pode ser lista ou string
                if isinstance(res_bar[1], list) and len(res_bar[1]) > 0:
                    identification_code = res_bar[1][0]
                elif isinstance(res_bar[1], str) and res_bar[1] != "":
                    identification_code = res_bar[1]

            if not identification_code:
                # Fallback: Tenta QR Code caso o código seja bidimensional
                res_qr = self.qrcode_detector.detectAndDecode(processed_img)
                if res_qr and res_qr[0]:
                    if isinstance(res_qr[0], str) and res_qr[0] != "":
                        identification_code = res_qr[0]

        except Exception as e:
            self.logger.error(f"Falha na inspeção: {str(e)}")

        response.identification_code = identification_code
        self.set_status(SystemServiceStatus.IDLE)
        
        if identification_code:
            self.logger.info(f"Sucesso! Código detectado: {identification_code}")
        else:
            self.logger.warn("Falha: Nenhum código identificado na PCI.")

        return response
     
    def align_images(current_img, golden_img, max_features=5000, keep_percent=0.2):
         """
         Alinha a imagem atual com a imagem de referência (Golden Image).
         
         :param current_img: Imagem capturada (pode estar torta/desalinhada).
         :param golden_img: O template perfeito.
         :param max_features: Quantidade máxima de pontos-chave a procurar.
         :param keep_percent: Porcentagem dos melhores matches a reter (filtra erros).
         :return: Imagem alinhada e a matriz de homografia (ou None se falhar).
         """
         # 1. Converter ambas para tons de cinza
         current_gray = cv.cvtColor(current_img, cv.COLOR_BGR2GRAY)
         golden_gray = cv.cvtColor(golden_img, cv.COLOR_BGR2GRAY)

         # 2. Inicializar o detector ORB
         orb = cv.ORB_create(max_features)

         # 3. Detectar pontos-chave (keypoints) e descritores em ambas as imagens
         (kps_curr, descs_curr) = orb.detectAndCompute(current_gray, None)
         (kps_gold, descs_gold) = orb.detectAndCompute(golden_gray, None)

         # Proteção: Se não achar pontos suficientes (imagem muito borrada, por ex)
         if descs_curr is None or descs_gold is None:
            return None, None

         # 4. Matcher: Encontrar as correspondências entre as duas imagens
         # Usa a distância de Hamming (ideal para ORB)
         matcher = cv.DescriptorMatcher_create(cv.DESCRIPTOR_MATCHER_BRUTEFORCE_HAMMING)
         matches = matcher.match(descs_curr, descs_gold)

         # 5. Ordenar os matches pela distância (os melhores ficam no topo da lista)
         matches = sorted(matches, key=lambda x: x.distance)

         # 6. Manter apenas os melhores X% dos matches para evitar falsos positivos
         keep = int(len(matches) * keep_percent)
         matches = matches[:keep]

         # Proteção: Precisamos de pelo menos 4 pontos para calcular a matriz 3D
         if len(matches) < 4:
            return None, None

         # 7. Extrair as coordenadas (x,y) dos melhores matches
         pts_curr = np.zeros((len(matches), 2), dtype="float")
         pts_gold = np.zeros((len(matches), 2), dtype="float")

         for (i, match) in enumerate(matches):
            pts_curr[i] = kps_curr[match.queryIdx].pt
            pts_gold[i] = kps_gold[match.trainIdx].pt

         # 8. Calcular a Matriz de Homografia usando RANSAC 
         # O RANSAC é o herói aqui: ele ignora matches absurdos (outliers)
         (H, mask) = cv.findHomography(pts_curr, pts_gold, method=cv.RANSAC)

         # Proteção de falha na matemática da matriz
         if H is None:
            return None, None

         # 9. Realizar a deformação (Warp) da imagem atual para bater com a Golden
         (height, width) = golden_img.shape[:2]
         aligned_img = cv.warpPerspective(current_img, H, (width, height))

         return aligned_img, H
      
      
def main():
    rclpy.init()
    service = Service()
    rclpy.spin(service)
    rclpy.shutdown()

if __name__ == "__main__":
    main()