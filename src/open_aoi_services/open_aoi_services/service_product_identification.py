import rclpy
import cv2 as cv
import numpy as np # Adicionado para manipulação de arrays

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
        # Inicializa detectores uma única vez para performance
        self.barcode_detector = cv.barcode.BarcodeDetector()
        self.qrcode_detector = cv.QRCodeDetector()

    def preprocess_image(self, image):
        """Aplica filtros para facilitar a leitura do código."""
        # 1. Correção de Cor (Caso esteja invertido BGR <-> RGB)
        # Se o azul está marrom, tente descomentar a linha abaixo:
        image = cv.cvtColor(image, cv.COLOR_BGR2RGB)

        # 2. Converter para Tons de Cinza (Essencial para detecção de padrões)
      #   gray = cv.cvtColor(image, cv.COLOR_BGR2GRAY)

        # 3. Aumentar Contraste (CLAHE é ótimo para inspeção industrial)
        clahe = cv.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        contrast_enhanced = clahe.apply(image)

        return contrast_enhanced

    def get_barcode(self, request, response):
        p = Profiler()
        self.logger.info(f"Iniciando inspeção de ID. [{p.tick()}]")
        self.set_status(SystemServiceStatus.BUSY)

        identification_code = ""
        try:
            # Converte imagem do ROS
            raw_image = imgmsg_to_cv2(request.image)
            
            # Pré-processamento
            processed_img = self.preprocess_image(raw_image)
            self.logger.info(f"Pré-processamento concluído. [{p.tick()}]")

            # Tenta detecção de Código de Barras
            ok, decoded_info, _, _ = self.barcode_detector.detectAndDecode(processed_img)
            
            if ok and decoded_info[0]:
                identification_code = decoded_info[0]
            else:
                # Fallback: Tenta QR Code caso o código seja bidimensional
                ok_qr, decoded_info_qr, _, _ = self.qrcode_detector.detectAndDecode(processed_img)
                if ok_qr:
                    identification_code = decoded_info_qr

            # Debug Visual (Opcional: salva a imagem que o algoritmo 'viu')
            # cv.imwrite('/tmp/last_inspection_debug.jpg', processed_img)

        except Exception as e:
            self.logger.error(f"Falha na inspeção: {str(e)}")

        response.identification_code = identification_code
        self.set_status(SystemServiceStatus.IDLE)
        
        if identification_code:
            self.logger.info(f"Sucesso! Código detectado: {identification_code}")
        else:
            self.logger.warn("Falha: Nenhum código identificado na PCI.")

        return response

def main():
    rclpy.init()
    service = Service()
    rclpy.spin(service)
    rclpy.shutdown()

if __name__ == "__main__":
    main()