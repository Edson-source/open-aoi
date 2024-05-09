from typing import Tuple

import cv2 as cv
import numpy as np
from PIL import Image

from open_aoi_core.content.modules import IModule
from open_aoi_core.exceptions import AssetIntegrityException


def scale(image: Image, width: int) -> Image:
    """Perform scale operation to desired width"""
    image_width, image_height = image.size
    ratio = image_height / image_width

    height = int(width * ratio)
    return image.resize((width, height))


def crop_stat_cv(im: np.ndarray, cv_stat_value: Tuple[int]) -> np.ndarray:
    """
    Function parse CV connected component detection statics (values)
    to cut out component from provided image
    """
    t = cv_stat_value[cv.CC_STAT_TOP]
    l = cv_stat_value[cv.CC_STAT_LEFT]

    w = cv_stat_value[cv.CC_STAT_WIDTH]
    h = cv_stat_value[cv.CC_STAT_HEIGHT]

    return im[t : t + h, l : l + w, :]


def crop_stat_image(image: Image.Image, cv_stat_value: Tuple[int]) -> Image.Image:
    """Wrapper for cropping PIL images"""
    image = np.array(image)
    image = crop_stat_cv(image, cv_stat_value)
    return Image.fromarray(image)


def isolate_product(image: np.ndarray, kernel_size: int = 31, threshold: int = 30):
    # Blur to vanish texture defects
    tmp = cv.cvtColor(image, cv.COLOR_BGR2GRAY)
    tmp = cv.medianBlur(tmp, kernel_size)

    # Arbitrary selected global threshold to separate background
    _, tmp = cv.threshold(tmp, threshold, 255, cv.THRESH_BINARY)

    analysis = cv.connectedComponentsWithStats(tmp, cv.CV_32S)
    (_, _, values, _) = analysis

    # Select the biggest connected component (product)
    mx, mxi = 0, 0
    for i, value in enumerate(values):
        area = value[cv.CC_STAT_AREA]
        if area >= mx and i != 0:
            mx = area
            mxi = i

    value = values[mxi]
    return crop_stat_cv(image, value)


def align(image: np.ndarray, template: np.ndarray, feature_point_amount: int = 1000):
    """Function perform alingment of two images using ORB algorithm (open source alternative for SURF)"""

    # Use ORB to detect keypoints and extract (binary) local
    # invariant features
    orb = cv.ORB_create(feature_point_amount)

    (kpsA, descsA) = orb.detectAndCompute(image, None)
    (kpsB, descsB) = orb.detectAndCompute(template, None)

    # Match the features
    method = cv.DESCRIPTOR_MATCHER_BRUTEFORCE_HAMMING
    matcher = cv.DescriptorMatcher_create(method)
    matches = matcher.match(descsA, descsB, None)

    # Sort the matches by their distance (the smaller the distance,
    # the "more similar" the features are)
    matches = sorted(matches, key=lambda x: x.distance)
    # keep only the top matches
    keep = int(len(matches) * 0.5)
    matches = matches[:keep]

    # Check to see if we should visualize the matched keypoints
    # matchedVis = cv.drawMatches(image, kpsA, template, kpsB, matches, None)
    # matchedVis = imutils.resize(matchedVis, width=1000)
    # imshow(matchedVis)

    # Allocate memory for the keypoints (x, y)-coordinates from the
    # top matches -- we'll use these coordinates to compute our
    # homography matrix
    pts_a = np.zeros((len(matches), 2), dtype="float")
    pts_b = np.zeros((len(matches), 2), dtype="float")
    # Loop over the top matches
    for i, m in enumerate(matches):
        # indicate that the two keypoints in the respective images
        # map to each other
        pts_a[i] = kpsA[m.queryIdx].pt
        pts_b[i] = kpsB[m.trainIdx].pt

    # Compute the homography matrix between the two sets of matched
    # points
    (H, mask) = cv.findHomography(pts_a, pts_b, method=cv.RANSAC)
    # Use the homography matrix to align the images
    (h, w) = template.shape[:2]
    image = cv.warpPerspective(image, H, (w, h))
    # Return the aligned image
    return image


def dynamic_import(source: bytes) -> Tuple[IModule, str]:
    """
    Import dynamically generated code as a module.
    """
    ctx = {}

    try:
        exec(source.decode(), ctx, ctx)
    except Exception as e:
        raise AssetIntegrityException(f"Failed to execute module: {str(e)}") from e

    try:
        assert ctx.get("DOCUMENTATION") is not None, "Documentation is missing."
        assert ctx.get("module") is not None, "Module instance function is missing."
        assert isinstance(
            ctx.get("module"), IModule
        ), "Module does not provide IModule interface."
    except AssertionError as e:
        raise AssetIntegrityException(f"Failed to validate module: {str(e)}") from e

    return ctx.get("module"), ctx.get("DOCUMENTATION")
