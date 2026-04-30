# Plate Alignment Inspection Module
# This module aligns the test image with the golden image and compares defects.

import numpy as np
import cv2 as cv
import logging
from typing import List

try:
    from open_aoi_core.content.modules import IModule
except ImportError:
    import sys
    sys.path.append("./src/open_aoi_core")
    from open_aoi_core.content.modules import IModule


DOCUMENTATION = """
Plate Alignment and Comparison Inspection Module

This module performs image registration (alignment) between the test image 
and the golden image using ORB features, then compares each inspection zone.

**Features:**
- Automatic image alignment using ORB feature detection
- Homography matrix computation for rotation/scale compensation
- Per-zone similarity comparison using histogram matching
- Detailed logging of alignment success/failure
- Threshold-based pass/fail decision per zone

**Required Parameters:**
- SIMILARITY_THRESHOLD: Float (0.0-1.0). Zones with similarity >= this value PASS. Default: 0.85
- MAX_FEATURES: Integer. Number of ORB features to detect. Default: 5000
- KEEP_PERCENT: Float (0.0-1.0). Percentage of best matches to keep. Default: 0.2
- ALIGNMENT_METHOD: String ('ORB' or 'ECC'). Default: 'ORB'

**Example Environment:**
SIMILARITY_THRESHOLD=0.85
MAX_FEATURES=5000
KEEP_PERCENT=0.2
ALIGNMENT_METHOD=ORB

**Expected Output:**
Each inspection zone returns a log with:
- Alignment status
- Similarity percentage for the zone
- Pass/Fail decision
"""


class Module(IModule):
    def __init__(self):
        self.logger = logging.getLogger("plate_alignment_inspection")
        self.logger_messages = []

    def align_images_orb(
        self,
        current_img: np.ndarray,
        golden_img: np.ndarray,
        max_features: int = 5000,
        keep_percent: float = 0.2,
    ) -> tuple:
        """
        Aligns current image with golden image using ORB features.
        
        Args:
            current_img: Test image (RGB)
            golden_img: Template/Golden image (BGR or RGB)
            max_features: Number of ORB features to detect
            keep_percent: Percentage of matches to keep after sorting
            
        Returns:
            (aligned_img, homography_matrix) or (None, None) if alignment fails
        """
        try:
            # Convert to grayscale
            current_gray = cv.cvtColor(current_img, cv.COLOR_RGB2GRAY)
            golden_gray = cv.cvtColor(golden_img, cv.COLOR_BGR2GRAY)

            # Initialize ORB detector
            orb = cv.ORB_create(max_features)

            # Detect keypoints and descriptors
            kps_curr, descs_curr = orb.detectAndCompute(current_gray, None)
            kps_gold, descs_gold = orb.detectAndCompute(golden_gray, None)

            # Protect against insufficient features
            if descs_curr is None or descs_gold is None:
                return None, None, "Insufficient features detected in one or both images"

            # Match descriptors
            matcher = cv.DescriptorMatcher_create(
                cv.DESCRIPTOR_MATCHER_BRUTEFORCE_HAMMING
            )
            matches = matcher.match(descs_curr, descs_gold)

            # Sort and filter matches
            matches = sorted(matches, key=lambda x: x.distance)
            keep = int(len(matches) * keep_percent)
            matches = matches[:keep]

            if len(matches) < 4:
                return None, None, f"Too few matches: {len(matches)} (minimum: 4)"

            # Extract point coordinates
            pts_curr = np.zeros((len(matches), 2), dtype="float32")
            pts_gold = np.zeros((len(matches), 2), dtype="float32")

            for i, match in enumerate(matches):
                pts_curr[i] = kps_curr[match.queryIdx].pt
                pts_gold[i] = kps_gold[match.trainIdx].pt

            # Compute homography matrix
            H, mask = cv.findHomography(pts_curr, pts_gold, method=cv.RANSAC)

            if H is None:
                return None, None, "Failed to compute homography matrix"

            # Warp the current image to align with golden image
            height, width = golden_img.shape[:2]
            aligned_img = cv.warpPerspective(current_img, H, (width, height))

            return aligned_img, H, f"Alignment successful ({len(matches)} matches used)"

        except Exception as e:
            return None, None, f"Alignment error: {str(e)}"

    def align_images_ecc(
        self,
        current_img: np.ndarray,
        golden_img: np.ndarray,
    ) -> tuple:
        """
        Aligns images using Enhanced Correlation Coefficient (ECC) method.
        Better for small rotations and deformations.
        
        Returns:
            (aligned_img, warp_matrix) or (None, None) if alignment fails
        """
        try:
            # Convert to grayscale
            current_gray = cv.cvtColor(current_img, cv.COLOR_RGB2GRAY)
            golden_gray = cv.cvtColor(golden_img, cv.COLOR_BGR2GRAY)

            # Define motion model (Homography requires 3x3 matrix)
            warp_mode = cv.MOTION_HOMOGRAPHY
            warp_matrix = np.eye(3, 3, dtype=np.float32)

            # Define termination criteria
            criteria = (
                cv.TERM_CRITERIA_EPS + cv.TERM_CRITERIA_COUNT,
                5000,
                1e-3,
            )

            # Run ECC algorithm
            cc, warp_matrix = cv.findTransformECC(
                golden_gray, current_gray, warp_matrix, warp_mode, criteria
            )

            # Warp the image
            height, width = golden_img.shape[:2]
            aligned_img = cv.warpPerspective(
                current_img, warp_matrix, (width, height)
            )

            return aligned_img, warp_matrix, f"ECC alignment successful (CC: {cc:.4f})"

        except Exception as e:
            return None, None, f"ECC alignment error: {str(e)}"

    def compute_zone_similarity(
        self,
        test_chunk: np.ndarray,
        template_chunk: np.ndarray,
    ) -> float:
        """
        Computes similarity between two image chunks using multiple methods.
        Returns a value between 0.0 (completely different) and 1.0 (identical).
        """
        try:
            # Log input shapes
            self.logger.info(f"compute_zone_similarity called with test_chunk shape: {test_chunk.shape if hasattr(test_chunk, 'shape') else 'NO SHAPE'}, template_chunk shape: {template_chunk.shape if hasattr(template_chunk, 'shape') else 'NO SHAPE'}")
            
            # Convert to grayscale for comparison
            if len(test_chunk.shape) == 3:
                test_gray = cv.cvtColor(test_chunk, cv.COLOR_RGB2GRAY)
            else:
                test_gray = test_chunk

            if len(template_chunk.shape) == 3:
                template_gray = cv.cvtColor(template_chunk, cv.COLOR_BGR2GRAY)
            else:
                template_gray = template_chunk

            # Ensure same size
            if test_gray.shape != template_gray.shape:
                self.logger.warning(f"Shape mismatch: test {test_gray.shape} vs template {template_gray.shape}. Resizing template...")
                template_gray = cv.resize(template_gray, (test_gray.shape[1], test_gray.shape[0]))

            # Histogram correlation (robust to lighting changes)
            hist_test = cv.calcHist([test_gray], [0], None, [256], [0, 256])
            hist_template = cv.calcHist([template_gray], [0], None, [256], [0, 256])

            # Normalize histograms
            hist_test = cv.normalize(hist_test, hist_test).flatten()
            hist_template = cv.normalize(hist_template, hist_template).flatten()

            # Compare histograms (returns value 0-1)
            similarity = cv.compareHist(
                hist_test, hist_template, cv.HISTCMP_CORREL
            )

            self.logger.info(f"Similarity computed: {similarity}")
            return max(0.0, min(1.0, similarity))  # Clamp to [0, 1]

        except Exception as e:
            # Log the error for debugging
            self.logger.error(f"Error in compute_zone_similarity: {str(e)}", exc_info=True)
            self.logger.error(f"test_chunk type: {type(test_chunk)}, template_chunk type: {type(template_chunk)}")
            if hasattr(test_chunk, 'shape'):
                self.logger.error(f"test_chunk shape: {test_chunk.shape}, dtype: {test_chunk.dtype}")
            if hasattr(template_chunk, 'shape'):
                self.logger.error(f"template_chunk shape: {template_chunk.shape}, dtype: {template_chunk.dtype}")
            return 0.0

    def process(
        self,
        environment: dict,
        test_image: np.ndarray,
        template_image: np.ndarray,
        inspection_zone_list: List[IModule.InspectionZone],
    ) -> List[IModule.InspectionLog]:
        """
        Main inspection process.
        
        1. Aligns test image with template image
        2. For each inspection zone:
           - Extracts both test and template chunks
           - Computes similarity
           - Compares against threshold
        3. Returns detailed logs
        """

        inspection_log_list = []

        # Extract parameters from environment
        similarity_threshold = float(
            environment.get("SIMILARITY_THRESHOLD", 0.85)
        )
        max_features = int(environment.get("MAX_FEATURES", 5000))
        keep_percent = float(environment.get("KEEP_PERCENT", 0.2))
        alignment_method = environment.get("ALIGNMENT_METHOD", "ORB").upper()

        # Step 1: Align images
        if alignment_method == "ECC":
            aligned_img, H, align_msg = self.align_images_ecc(test_image, template_image)
        else:  # Default to ORB
            aligned_img, H, align_msg = self.align_images_orb(
                test_image, template_image, max_features, keep_percent
            )

        alignment_success = aligned_img is not None

        # Step 2: Process each inspection zone
        for i, zone in enumerate(inspection_zone_list):
            zone_number = i + 1

            if not alignment_success:
                # If alignment failed, mark zones as failed
                inspection_log_list.append(
                    IModule.InspectionLog(
                        f"Zone {zone_number}: FAILED - Image alignment failed. {align_msg}",
                        False,
                    )
                )
                continue

            try:
                # Extract chunks from both images
                test_chunk = self.cut_inspection_zone(aligned_img, zone)
                template_chunk = self.cut_inspection_zone(template_image, zone)

                if test_chunk is None or template_chunk is None:
                    inspection_log_list.append(
                        IModule.InspectionLog(
                            f"Zone {zone_number}: ERROR - Failed to extract zone region.",
                            False,
                        )
                    )
                    continue

                # Compute similarity
                similarity = self.compute_zone_similarity(test_chunk, template_chunk)
                similarity_percent = similarity * 100

                # Determine pass/fail
                passed = similarity >= similarity_threshold

                # Build log message
                status = "PASS" if passed else "FAIL"
                log_msg = (
                    f"Zone {zone_number}: {status} "
                    f"(Similarity: {similarity_percent:.1f}%, "
                    f"Threshold: {similarity_threshold*100:.1f}%)"
                )

                inspection_log_list.append(
                    IModule.InspectionLog(log_msg, passed)
                )

            except Exception as e:
                inspection_log_list.append(
                    IModule.InspectionLog(
                        f"Zone {zone_number}: ERROR - {str(e)}", False
                    )
                )

        return inspection_log_list


# Module instance required by Open AOI
module = Module()
