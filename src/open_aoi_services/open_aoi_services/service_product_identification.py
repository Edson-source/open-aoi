"""
    This script is an identification service source code. See service definition for request format.
    Service provide product identification data decoding (like barcode). 
"""

import rclpy
import cv2 as cv2

from open_aoi_interfaces.srv import IdentificationTrigger
from open_aoi_core.services import StandardService
from open_aoi_core.utils_basic import isolate_product, Profiler
from open_aoi_core.utils_ros import message_to_image
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

    def get_barcode(self, request, response):
        p = Profiler()
        self.logger.info(f"Barcode identification triggered. [{p.tick()}]")
        self.set_status(SystemServiceStatus.BUSY)

        identification_code = ""
        try:
            im = message_to_image(request.image)
            self.logger.info(f"Message converted to image. [{p.tick()}]")

            isolated = isolate_product(im)  # TODO: remove
            self.logger.info(f"Product isolated. [{p.tick()}]")

            isolated = cv2.resize(  # TODO: remove
                isolated, (1000, 1000), interpolation=cv2.INTER_LINEAR
            )
            self.logger.info(f"Image resized. [{p.tick()}]")

            bardet = cv2.barcode.BarcodeDetector()
            identification_code, *_ = bardet.detectAndDecode(im)
            self.logger.info(f"Barcode identified and decoded. [{p.tick()}]")
        except Exception as e:
            self.logger.error(str(e))
        response.identification_code = identification_code

        self.set_status(SystemServiceStatus.IDLE)
        self.logger.info(f"Barcode detected: {identification_code}")

        return response


def main():
    rclpy.init()
    service = Service()
    rclpy.spin(service)
    rclpy.shutdown()


if __name__ == "__main__":
    main()
