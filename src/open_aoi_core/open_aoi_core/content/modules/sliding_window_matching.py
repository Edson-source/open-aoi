# Sliding Window Pattern Matching
# This module dynamically searches for the template component on the entire test image
# using sliding window (template matching), ignoring the static position of the box.

try:
    from open_aoi_core.content.modules import IModule  # Import module interface
except ImportError:
    import sys  # Add core library to the path for development
    sys.path.append("./src/open_aoi_core")
    from open_aoi_core.content.modules import IModule  # Import module interface

import cv2
import numpy as np
from typing import List

DOCUMENTATION = """
This module uses a sliding window (cv2.matchTemplate) to find the component
anywhere on the tested PCB, instead of relying on the strict position of the
inspection box. It's useful if the board is shifted or if the exact position varies.

Required parameters:
- SLIDING_WINDOW_MATCH_THRESHOLD: float, from 0 to 1. The minimum similarity score
  required to consider the component present. Example: 0.8.
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
            MATCH_THRESHOLD = float(environment.get("SLIDING_WINDOW_MATCH_THRESHOLD", 0.8))
        except Exception as e:
            raise RuntimeError("Parameters are missing or malformed.") from e

        # Ensure images are in grayscale for template matching
        if len(test_image.shape) == 3:
            test_gray = cv2.cvtColor(test_image, cv2.COLOR_BGR2GRAY)
        else:
            test_gray = test_image

        if len(template_image.shape) == 3:
            template_gray = cv2.cvtColor(template_image, cv2.COLOR_BGR2GRAY)
        else:
            template_gray = template_image

        inspection_log_list = []

        for zone in inspection_zone_list:
            # 1. Cut the target component from the template image using the zone
            target_patch = self.cut_inspection_zone(template_gray, zone)

            # Basic sanity check
            if target_patch is None or target_patch.size == 0:
                inspection_log_list.append(
                    IModule.InspectionLog("Invalid template patch size.", False)
                )
                continue

            # If the patch is larger than the test image for some reason, it will fail
            if target_patch.shape[0] > test_gray.shape[0] or target_patch.shape[1] > test_gray.shape[1]:
                inspection_log_list.append(
                    IModule.InspectionLog("Target patch larger than test image.", False)
                )
                continue

            # 2. Perform Sliding Window Template Matching over the ENTIRE test image
            result = cv2.matchTemplate(test_gray, target_patch, cv2.TM_CCOEFF_NORMED)

            # 3. Find the best match
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

            # 4. Check if the best match score is above our threshold
            passed = max_val >= MATCH_THRESHOLD

            if passed:
                log_msg = f"Component found dynamically at (x={max_loc[0]}, y={max_loc[1]}) with score {max_val:.2f}."
            else:
                log_msg = f"Component missing or not matched well enough. Max score: {max_val:.2f}."

            inspection_log_list.append(
                IModule.InspectionLog(log_msg, passed)
            )

        return inspection_log_list

module = Module()
