"""
    This script is an identification service source code. See service definition for request format.
    Service provide product identification data decoding (like barcode). 
"""

import rclpy
from rclpy.node import Node

import cv2 as cv

from open_aoi_ros_interfaces.srv import IdentificationTrigger, ServiceStatus
from open_aoi_core.services.utils import decode_image

NODE_NAME = "identification"


class Service(Node):
    service_status_default: str = "Working"
    service_status: str = service_status_default

    def __init__(self):
        super().__init__(NODE_NAME)
        # --- Services ---
        self.registration_service = self.create_service(
            IdentificationTrigger,
            f"{NODE_NAME}/get_barcode",
            self.identify_barcode,
        )

        self.status_service = self.create_service(
            ServiceStatus,
            f"{NODE_NAME}/get_status",
            self.expose_status,
        )

        self.logger = self.get_logger()
        self.logger.info("Service started")

    def _set_status(self, msg: str):
        self.service_status = msg

    def expose_status(self, request, response):
        self.logger.info("Status requested")
        response.status = self.service_status
        return response

    def identify_barcode(self, request, response):
        self.logger.info("Barcode identification triggered")
        im = decode_image(request.image)
        
        bardet = cv.barcode.BarcodeDetector()
        identification_code, *_ = bardet.detectAndDecode(im)
        
        response.identification_code = identification_code
        return response


def main():
    rclpy.init()
    service = Service()

    rclpy.spin(service)
    rclpy.shutdown()


if __name__ == "__main__":
    main()
