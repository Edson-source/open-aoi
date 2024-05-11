# Capacitor opposite orientation.
# This module identify opposite orientation of capacitor in the chunk.


from typing import List

import cv2 as cv2
import numpy as np

try:
    from open_aoi_core.content.modules import IModule  # Import module interface
except ImportError:
    import sys  # Add core library to the path for development (in production it will be available without this)

    sys.path.append("./src/open_aoi_core")
    from open_aoi_core.content.modules import IModule  # Import module interface

DOCUMENTATION = """
This module identify opposite orientation of capacitor in the chunk.

Required parameters:
- CAP_ORIENT_OPP_THRESHOLD: integer, from 0 to 255. Used for binarization of absolute difference of two images.
- CAP_ORIENT_OPP_EROSION_ITERATIONS: any integer. Used to remove noise in the difference of two images.
- CAP_ORIENT_OPP_KERNEL_SIZE: any integer. Used for erosion operation for define kernel size.
"""


class Module(IModule):
    def process(
        self,
        environment: dict,
        test_image: np.ndarray,
        template_image: np.ndarray,
        inspection_zone_list: List[IModule.InspectionZone],
    ) -> List[IModule.InspectionLog]:

        try:
            CAP_ORIENT_OPP_THRESHOLD = int(environment["CAP_ORIENT_OPP_THRESHOLD"])
            CAP_ORIENT_OPP_EROSION_ITERATIONS = int(
                environment["CAP_ORIENT_OPP_EROSION_ITERATIONS"]
            )
            CAP_ORIENT_OPP_KERNEL_SIZE = int(environment["CAP_ORIENT_OPP_KERNEL_SIZE"])
        except Exception as e:
            raise RuntimeError("Parameters are missing or malformed.") from e

        inspection_log_list = []
        for i, zone in enumerate(inspection_zone_list):

            test_chunk = self.cut_inspection_zone(test_image, zone)
            template_chunk = self.cut_inspection_zone(template_image, zone)

            # Calc abs difference
            difference = cv2.absdiff(template_chunk, test_chunk)

            # Apply threshold
            _, difference_threshold = cv2.threshold(
                difference, CAP_ORIENT_OPP_THRESHOLD, 255, cv2.THRESH_BINARY
            )

            # Apply erosion
            kernel = np.ones(
                (CAP_ORIENT_OPP_KERNEL_SIZE, CAP_ORIENT_OPP_KERNEL_SIZE), np.uint8
            )
            difference_erode = cv2.erode(
                difference_threshold,
                kernel,
                iterations=CAP_ORIENT_OPP_EROSION_ITERATIONS,
            )

            # Apply the Component analysis function
            (total_labels, _, _, _) = cv2.connectedComponentsWithStats(
                difference_erode, 4, cv2.CV_32S
            )

            passed = total_labels - 1 <= 1

            inspection_log_list.append(
                IModule.InspectionLog(f"Components detected: {total_labels}", passed)
            )
        return inspection_log_list


module = Module()
