import base64
import pickle
from typing import Optional, Tuple

import roslibpy
from PIL import Image

from open_aoi.controllers.ros_services import Service
from open_aoi.exceptions import ROSServiceError


class ROSImageAcquisitionService(Service):
    _service_name = "image_acquisition"

    ERROR_NONE = "NONE"

    def __init__(self, camera_ip: Optional[str] = None, emulator: bool = False) -> None:
        super().__init__()
        self.camera_ip = camera_ip
        self.emulator = emulator

    def _publish_service_parameters(self):
        ros = self._get_ros_client()
        ros.set_param(f"{self._service_name}:camera_enabled", True)
        ros.set_param(f"{self._service_name}:camera_emulation_mode", True)

    def capture(self) -> Tuple[Image.Image, str, str]:
        try:
            self._publish_service_parameters()
            ros = self._get_ros_client()
            service = roslibpy.Service(
                ros,
                f"{self._service_name}/capture",
                "open_aoi_interfaces/ImageAcquisition",
            )
            request = roslibpy.ServiceRequest()
            response = service.call(request, timeout=10)

            error = response["error"]
            error_description = response["error_description"]
            im = pickle.loads(base64.decodebytes(response["image"]["data"].encode()))
            im = Image.fromarray(im)

            return im, error, error_description
        except:
            raise ROSServiceError("Failed to obtain service status")
