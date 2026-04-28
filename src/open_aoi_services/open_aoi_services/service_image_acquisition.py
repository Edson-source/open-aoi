import os
import random
from typing import List, Optional

import cv2
import rclpy
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
    camera_index: Optional[int] = None

    emulation_images = [f for f in os.listdir(EMULATION_DIR) if ".png" in f]

    def __init__(self):
        super().__init__()

        self.acquire_image_service = self.create_service(
            ImageAcquisitionTrigger,
            f"{self.NODE_NAME}/capture",
            self.acquire_image,
        )

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
                description="IP address of camera to use.",
            ),
        )

        self.add_on_set_parameters_callback(self._update_parameters)
        self._reload_service()

    def _update_parameters(self, parameters: List[rclpy.Parameter]):
        self.logger.info("Parameters update triggered")
        reload = False
        for p in parameters:
            self.logger.info(f"Parameter {p.name}: {getattr(self, p.name)} -> {p.value}")
            setattr(self, p.name, p.value)
            if p.name == ImageAcquisitionConstants.Parameter.CAMERA_ENABLED:
                reload = True
        if reload: 
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

        if SIMULATION:
            self.logger.info("Running emulation mode (Ignorado)")
            self.set_status(SystemServiceStatus.IDLE, "Emulation mode is disabled.")
            return
        else:
            self.logger.info(f"Running with WEBCAM via OpenCV")
            try:
                self.camera_index = "http://host.docker.internal:5000/video"
                
                cap = cv2.VideoCapture(self.camera_index)
                cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
                cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1) 
                cap.set(cv2.CAP_PROP_EXPOSURE, -5)

                if not cap.isOpened():
                     raise Exception("OpenCV não conseguiu abrir o stream da camera")
                cap.release()

                self.set_status(SystemServiceStatus.IDLE, f"Connected to webcam at {self.camera_index}")
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
            response.error_description = "Capture image called before camera initialization"
            self.set_status(SystemServiceStatus.IDLE)
            return response
            
        try:
            cap = cv2.VideoCapture(self.camera_index)
            
            for _ in range(5):
                cap.grab()
                
            ret, frame = cap.read()
            cap.release()

            if ret:
                self.logger.info(f"Grabbed successfully: {frame.shape}. [{p.tick()}]")
                
                # CORREÇÃO AQUI: Converte a imagem capturada em BGR para RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) 
                
                # Envia a imagem RGB para o ROS
                response.image = cv2_to_imgmsg(frame_rgb)
                response.error = ImageAcquisitionConstants.Error.NONE
                response.error_description = ""
                self.logger.info(f"Image returned. [{p.tick()}]")
                self.set_status(SystemServiceStatus.IDLE)
                return response
            else:
                self.logger.error("Webcam read return false (Grabbed unsuccessfully).")
                response.error = ImageAcquisitionConstants.Error.GENERAL
                response.error_description = "Capture image failed from Webcam"
                self.set_status(SystemServiceStatus.IDLE)
                return response
        except Exception as e:
            self.logger.error(str(e))
            response.error = ImageAcquisitionConstants.Error.GENERAL
            response.error_description = "Capture image failed"
            self.set_status(SystemServiceStatus.IDLE)
            return response

def main():
    rclpy.init()
    service = Service()
    rclpy.spin(service)
    rclpy.shutdown()

if __name__ == "__main__":
    main()