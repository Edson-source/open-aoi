from typing import List
import numpy as np
import cv2 as cv
from PIL import Image


def crop_stat_cv(im: np.ndarray, cv_stat_value: List[int]) -> np.ndarray:
    # Function parse CV connected component detection statics (values)
    # to cut out component from provided image
    t = cv_stat_value[cv.CC_STAT_TOP]
    l = cv_stat_value[cv.CC_STAT_LEFT]

    w = cv_stat_value[cv.CC_STAT_WIDTH]
    h = cv_stat_value[cv.CC_STAT_HEIGHT]

    return im[t : t + h, l : l + w]


def crop_stat_image(im: Image.Image, cv_stat_value: List[int]) -> Image.Image:
    # Wrapper for cropping PIL images
    im = np.array(im)
    im = crop_stat_cv(im, cv_stat_value)
    return Image.fromarray(im)


def isolate_product(im: np.ndarray, kernel_size: int = 31, threshold: int = 30):
    # Blur to vanish texture defects
    im = cv.medianBlur(im, kernel_size)

    # Arbitrary selected global threshold to separate background
    _, im = cv.threshold(im, threshold, 255, cv.THRESH_BINARY)

    analysis = cv.connectedComponentsWithStats(im, cv.CV_32S)
    (_, _, values, _) = analysis

    # Select the biggest connected component (product)
    mx, mxi = 0, 0
    for i, value in enumerate(values):
        area = value[cv.CC_STAT_AREA]
        if area >= mx:
            mxi = i

    value = values[mxi]
    return crop_stat_cv(im, value)


def align(im: np.ndarray, template: np.ndarray, feature_point_amount: int = 1000):
    # Function perform alingment of two images using ORB algorithm (open source alternative for SURF)

    # Use ORB to detect keypoints and extract (binary) local
    # invariant features
    orb = cv.ORB_create(feature_point_amount)

    (kpsA, descsA) = orb.detectAndCompute(im, None)
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
    # matchedVis = cv.drawMatches(im, kpsA, template, kpsB, matches, None)
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
    im = cv.warpPerspective(im, H, (w, h))
    # Return the aligned image
    return im
