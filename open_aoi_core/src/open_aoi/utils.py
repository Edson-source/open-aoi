import numpy as np
import cv2 as cv
from PIL import Image


def crop_stat_cv(im: np.ndarray, cv_stat_value: list[int]) -> np.ndarray:
    # Function parse CV connected component detection statics (values)
    # to cut out component from provided image
    t = cv_stat_value[cv.CC_STAT_TOP]
    l = cv_stat_value[cv.CC_STAT_LEFT]

    w = cv_stat_value[cv.CC_STAT_WIDTH]
    h = cv_stat_value[cv.CC_STAT_HEIGHT]

    return im[t : t + h, l : l + w]


def crop_stat_image(im: Image.Image, cv_stat_value: list[int]) -> Image.Image:
    # Wrapper for cropping PIL images
    im = np.array(im)
    im = crop_stat_cv(im, cv_stat_value)
    return Image.fromarray(im)
