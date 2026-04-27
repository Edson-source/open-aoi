import os
import random
from typing import List, Optional

import cv2 # IMPORTAMOS O OPENCV AQUI
import rclpy
# from pypylon import pylon  <- REMOVIDO PARA PARAR DE BUSCAR CAMERA INDUSTRIAL
from rcl_interfaces.msg import ParameterDescriptor, SetParametersResult

from open_aoi_interfaces.srv import ImageAcquisitionTrigger
from open_aoi_core.settings import SIMULATION
from open_aoi_core.utils_ros import cv2_to_imgmsg
from open_aoi_core.utils_basic import Profiler
from open_aoi_core.constants import ImageAcquisitionConstants, SystemServiceStatus
from open_aoi_core.services import StandardService

EMULATION_DIR = "./emulation"


class Service(StandardService):
    NODE_NAME = ImageAcquisitionConstants.NODE_NAME

    CAMERA_IP_ADDRESS: str = ""
    CAMERA_ENABLED: bool = False

    # camera: Optional[pylon.InstantCamera] = None <- REMOVIDO
    camera_index: Optional[int] = None # ADICIONADO PARA GUARDAR O ÍNDICE DA WEBCAM

    emulation_images = [f for f in os.listdir(EMULATION_DIR) if ".png" in f]

    def __init__(self):
        super().__init__()

        # --- Services ---
        self.acquire_image_service = self.create_service(
            ImageAcquisitionTrigger,
            f"{self.NODE_NAME}/capture",
            self.acquire_image,
        )

        # --- Parameters ---
        self.declare_parameter(
            ImageAcquisitionConstants.Parameter.CAMERA_ENABLED,
            value=self.CAMERA_ENABLED,
            descriptor=ParameterDescriptor(
                name="Camera enabled",
                type=rclpy.Parameter.Type.BOOL.value,
                description="If True, connection to camera will be opened. False by default.",
            ),
        )
        self.declare_parameter(
            ImageAcquisitionConstants.Parameter.CAMERA_IP_ADDRESS,
            value=self.CAMERA_IP_ADDRESS,
            descriptor=ParameterDescriptor(
                name="Camera IP address",
                type=rclpy.Parameter.Type.STRING.value,
                description="IP address of camera to use. If not provided, node will connect to the first found camera.",
            ),
        )

        self.add_on_set_parameters_callback(self._update_parameters)
        self._reload_service()

    def _update_parameters(self, parameters: List[rclpy.Parameter]):
        self.logger.info("Parameters update triggered")
        reload = False
        for p in parameters:
            self.logger.info(
                f"Parameter {p.name}: {getattr(self, p.name)} -> {p.value}"
            )
            setattr(self, p.name, p.value)
            if p.name == ImageAcquisitionConstants.Parameter.CAMERA_ENABLED:
                reload = True
        if (
            reload
        ):  # This function is triggered multiple times for unknown reason - reload services only once though
            self._reload_service()
        self.logger.info("Parameters update done")
        return SetParametersResult(successful=True, reason="")

    def _reload_service(self):
        self.logger.info("Service reload requested")
        self.logger.info(f"Service enabled: {self.CAMERA_ENABLED}")
        if self.CAMERA_ENABLED:
            self._acquire_camera()

    def _acquire_camera(self):
        self.logger.info("Camera connection requested")

        # Emulation (Mantido para caso você ligue o .env novamente)
        if SIMULATION:
            self.logger.info("Running emulation mode (Ignorado pois SIMULATION=0)")
            # ... toda a lógica de emulação pylon foi limpa para evitar dependências desnecessárias, 
            # já que o foco é a webcam USB agora.
            self.set_status(SystemServiceStatus.IDLE, "Emulation mode requires pypylon, which is disabled.")
            return

        # Real camera via OpenCV (Nossa WebCam)
        else:
            self.logger.info(f"Running with WEBCAM via OpenCV")
            try:
                # O /dev/video0 é o índice 0 no OpenCV. Se o IP não for numérico, assume 0.
                self.camera_index = "http://host.docker.internal:5000/video"  # URL do stream da webcam
                
                # Fazemos um pequeno teste silencioso só para ver se a câmera existe
                cap = cv2.VideoCapture(self.camera_index)
                if not cap.isOpened():
                     raise Exception("OpenCV não conseguiu abrir /dev/video0")
                cap.release()

                self.set_status(
                    SystemServiceStatus.IDLE,
                    f"Connected to webcam at /dev/video{self.camera_index}",
                )
                return
            except Exception as e:
                self.logger.error(str(e))
                self.set_status(SystemServiceStatus.ERROR, "Failed to setup webcam")
                return

    def acquire_image(self, request, response):
        p = Profiler()

        self.logger.info(f"Image requested. [{p.tick()}]")
        self.set_status(SystemServiceStatus.BUSY)

        if self.camera_index is None:
            self.logger.error("Camera index not initialized")
            response.error = ImageAcquisitionConstants.Error.GENERAL
            response.error_description = (
                "Capture image called before camera initialization"
            )
            self.set_status(SystemServiceStatus.IDLE)
            self.logger.info(f"Response returned. [{p.tick()}]")
            return response
            
        try:
            # AQUI A MÁGICA ACONTECE: O OpenCV abre a câmera, bate a foto e fecha.
            cap = cv2.VideoCapture(self.camera_index)
            
            # Limpa o buffer antigo (Webcams costumam guardar frames velhos no buffer do Linux)
            for _ in range(5):
                cap.grab()
                
            ret, frame = cap.read()
            cap.release()

            if ret:
                self.logger.info(f"Grabbed successfully: {frame.shape}. [{p.tick()}]")
                # Se necessário, converte de BGR para RGB para compatibilidade de cor
                # frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) 
                
                response.image = cv2_to_imgmsg(frame)
                response.error = ImageAcquisitionConstants.Error.NONE
                response.error_description = ""
                self.logger.info(f"Image returned. [{p.tick()}]")
                self.set_status(SystemServiceStatus.IDLE)
                return response
            else:
                self.logger.error("Webcam read return false (Grabbed unsuccessfully).")
                response.error = ImageAcquisitionConstants.Error.GENERAL
                response.error_description = "Capture image failed from Webcam"
                self.logger.info("Response returned")
                self.set_status(SystemServiceStatus.IDLE)
                return response
        except Exception as e:
            self.logger.error(str(e))
            response.error = ImageAcquisitionConstants.Error.GENERAL
            response.error_description = "Capture image failed"
            self.set_status(SystemServiceStatus.IDLE)
            self.logger.info("Response returned")
            return response


def main():
    rclpy.init()
    service = Service()

    rclpy.spin(service)
    rclpy.shutdown()


if __name__ == "__main__":
    main()