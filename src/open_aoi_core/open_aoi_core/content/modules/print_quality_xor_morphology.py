# Print quality
# This module identify print issues


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
- PRINT_Q_ALLOWED_DIFFERENCE: float, from 0 to 1. Allowed percentage of difference between images.
"""


def align_arrays(array1, array2):
    """
    Aligns array1 based on cross-correlation with array2. Used to fine-align cut chunks

    Args:
        array1: Numpy array of shape (N, M)
        array2: Numpy array of shape (N, M)

    Returns:
        aligned_array1: Numpy array of shape (N, M), aligned with array2
    """
    best_score = -np.inf
    best_shift = (0, 0)

    # Loop over each possible overlap of arrays
    for i in range(-array1.shape[0] + 1, array2.shape[0]):
        for j in range(-array1.shape[1] + 1, array2.shape[1]):
            # Shift array1
            shifted_array1 = np.roll(array1, (i, j), axis=(0, 1))

            # Compute correlation score
            score = np.sum(shifted_array1 * array2)

            # Update best score and shift if this is the best so far
            if score > best_score:
                best_score = score
                best_shift = (i, j)

    # Apply the best shift to align array1 with array2
    aligned_array1 = np.roll(array1, best_shift, axis=(0, 1))

    return aligned_array1


def image_normalization(im: np.ndarray):
    _, im = cv2.threshold(im, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return im


class Module(IModule):
    def process(
        self,
        environment: dict,
        test_image: np.ndarray,
        template_image: np.ndarray,
        inspection_zone_list: List[IModule.InspectionZone],
    ) -> List[IModule.InspectionLog]:
        try:
            ALLOWED_DIFFERENCE = int(environment["PRINT_Q_ALLOWED_DIFFERENCE"])
        except Exception as e:
            raise RuntimeError("Parameters are missing or malformed.") from e

        inspection_log_list = []
        for i, zone in enumerate(inspection_zone_list):

            test_chunk = image_normalization(self.cut_inspection_zone(test_image, zone))
            template_chunk = image_normalization(
                self.cut_inspection_zone(template_image, zone)
            )

            test_chunk = align_arrays(test_chunk, template_chunk)

            total = test_chunk.size
            delta = np.logical_xor(template_chunk, test_chunk).sum()
            diff = delta / total
            
            passed = diff <= ALLOWED_DIFFERENCE

            inspection_log_list.append(
                IModule.InspectionLog(f"Detected difference {diff * 100}%", passed)
            )
        return inspection_log_list


module = Module()
