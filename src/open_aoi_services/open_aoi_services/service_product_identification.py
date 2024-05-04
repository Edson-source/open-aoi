"""
    This script is an identification service source code. See service definition for request format.
    Service provide product identification data decoding (like barcode). 
"""

import rclpy
import cv2 as cv
from rclpy.executors import MultiThreadedExecutor

from open_aoi_core.services import StandardService
from open_aoi_interfaces.srv import IdentificationTrigger
from open_aoi_core.utils import decode_image, isolate_product
from open_aoi_core.constants import ProductIdentificationConstants, ServiceStatusEnum


class Service(StandardService):
    NODE_NAME = ProductIdentificationConstants.NODE_NAME

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
        self.set_status(ServiceStatusEnum.BUSY.value)

        try:
            im = decode_image(request.image)

            isolated = isolate_product(im)  # TODO: set as parameters
            isolated = cv.resize(isolated, (1000, 1000), interpolation=cv.INTER_LINEAR) 

            bardet = cv.barcode.BarcodeDetector()
            identification_code, *_ = bardet.detectAndDecode(im)

            response.identification_code = identification_code
        except Exception as e:
            # No errors expected
            self.logger.error(str(e))

        self.set_status(ServiceStatusEnum.IDLE.value)
        self.logger.info(f"Barcode identification returned: {identification_code}")
        return response


def main():
    rclpy.init()
    service = Service()

    executor = MultiThreadedExecutor(10)
    executor.add_node(service)

    executor.spin()

    executor.shutdown()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
