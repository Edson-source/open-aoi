"""
    This script is an identification service source code. See service definition for request format.
    Service provide product identification data decoding (like barcode). 
"""

import rclpy

import cv2 as cv

from open_aoi_ros_services import StandardService
from open_aoi_ros_interfaces.srv import IdentificationTrigger
from open_aoi_core.utils import decode_image
from open_aoi_core.constants import ProductIdentificationEnum, ServiceStatusEnum


class Service(StandardService):
    NODE_NAME = ProductIdentificationEnum.NODE_NAME.value

    def __init__(self):
        super().__init__()
        # --- Services ---
        self.registration_service = self.create_service(
            IdentificationTrigger,
            f"{self.NODE_NAME}/get_barcode",
            self.get_barcode,
        )

    def get_barcode(self, request, response):
        self.logger.info("Barcode identification triggered")
        self._set_status(ServiceStatusEnum.BUSY.value)

        try:
            im = decode_image(request.image)

            bardet = cv.barcode.BarcodeDetector()
            identification_code, *_ = bardet.detectAndDecode(im)

            response.identification_code = identification_code
        except Exception as e:
            # No errors expected
            self.logger.error(str(e))

        self._set_status(ServiceStatusEnum.IDLE.value)
        return response


def main():
    rclpy.init()
    service = Service()

    rclpy.spin(service)
    rclpy.shutdown()


if __name__ == "__main__":
    main()
