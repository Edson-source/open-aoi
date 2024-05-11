# Component presence with histogram backprojection
# This module identify component presence defect type

try:
    from open_aoi_core.content.modules import IModule  # Import module interface
except ImportError:
    import sys  # Add core library to the path for development (in production it will be available without this)

    sys.path.append("./src/open_aoi_core")
    from open_aoi_core.content.modules import IModule  # Import module interface

from typing import List

import cv2
import numpy as np


DOCUMENTATION = """
This module identify component presence on colored image. It expect product to fill most of the image (80-90%). 
Inspection zones should be placed on such places, that when component is missing, the background of
PCB is visible. Make such inspection zone as large as possible.

Required parameters
- COMP_PRES_HBP_BINS_LB: integer. Lower limit for HBP weighting
- COMP_PRES_HBP_BINS_UB: integer. Upper limit for HBP weighting
- COMP_PRES_HBP_BACKGROUND_PROBABILITY_THRESHOLD: float, from 0 to 1. Lower bound for pixel probability to be classified as background
- COMP_PRES_HBP_KERNEL_SIZE: integer. Kernel size for median filter
- COMP_PRES_HBP_ACCEPTABLE_BACKGROUND_RATIO: float, from 0 to 1. Maximal allowed ratio of background in the image
"""


def back_projection(image: np.ndarray, bins: int, mask: np.ndarray = None):
    # Calculate histogram over cropped image (crop to offset * original width/hight) to minimize influence of
    # possible global background remainders
    ranges = [0, 180]
    hist_size = max(bins, 2)
    hist = cv2.calcHist([image], [0], mask, [hist_size], ranges, accumulate=False)
    cv2.normalize(hist, hist, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX)

    return cv2.calcBackProject([image], [0], hist, ranges, scale=1)


def weighted_back_projection(
    image: np.ndarray, bins_lb, bins_ub, mask: np.ndarray = None
):
    # Perform weighted histogram back projection
    hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
    image = np.empty(hsv.shape, hsv.dtype)
    cv2.mixChannels([hsv], [image], (0, 0))

    # Weight is just inversion of bin size
    image_hbp = back_projection(image, bins_lb, mask).astype(float)
    for bins in range(bins_lb + 1, bins_ub):
        image_hbp += (1 / bins) * back_projection(image, bins)

    return (image_hbp / image_hbp.max() * 255).astype(np.uint8)


class Module(IModule):
    def process(
        self,
        environment: dict,
        test_image: np.ndarray,
        template_image: np.ndarray,
        inspection_zone_list: List[IModule.InspectionZone],
    ) -> List[IModule.InspectionLog]:
        try:
            BINS_LB = int(environment["COMP_PRES_HBP_BINS_LB"])
            BINS_UB = int(environment["COMP_PRES_HBP_BINS_UB"])
            KERNEL_SIZE = int(environment["COMP_PRES_HBP_KERNEL_SIZE"])
            BACKGROUND_PROBABILITY_THRESHOLD = float(
                environment["COMP_PRES_HBP_BACKGROUND_PROBABILITY_THRESHOLD"]
            )
            ACCEPTABLE_BACKGROUND_RATIO = float(
                environment["COMP_PRES_HBP_ACCEPTABLE_BACKGROUND_RATIO"]
            )
        except Exception as e:
            raise RuntimeError("Parameters are missing or malformed.") from e

        test_image_hbp = weighted_back_projection(test_image, BINS_LB, BINS_UB)

        inspection_log_list = []
        for i, zone in enumerate(inspection_zone_list):

            test_chunk = self.cut_inspection_zone(test_image_hbp, zone)
            test_chunk = test_chunk < (255 * BACKGROUND_PROBABILITY_THRESHOLD)
            test_chunk = cv2.medianBlur(test_chunk.astype(np.uint8), KERNEL_SIZE)

            ratio = test_chunk.sum() / test_chunk.size
            passed = ratio <= ACCEPTABLE_BACKGROUND_RATIO

            inspection_log_list.append(
                IModule.InspectionLog(f"Detected background ratio: {ratio}", passed)
            )
        return inspection_log_list


module = Module()
