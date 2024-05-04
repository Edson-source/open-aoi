import numpy as np
from typing import List
from open_aoi_core.content.modules import IModule


def iter_average_h(im: np.ndarray):
    r, c = im.shape[0], im.shape[1]
    res = np.zeros((r, int(np.floor(c / 2))))
    for i in range(int(np.floor(c / 2))):
        res[:, i] = (im[:, 2 * i - 1] + im[:, 2 * i]) / 2
    return res


def iter_difference_h(im: np.ndarray):
    r, c = im.shape[0], im.shape[1]
    res = np.zeros((r, int(np.floor(c / 2))))
    for i in range(int(np.floor(c / 2))):
        res[:, i] = (im[:, 2 * i] - im[:, 2 * i - 1]) / 2
    return res


def iter_average_v(im: np.ndarray):
    r, c = im.shape[0], im.shape[1]
    res = np.zeros((int(np.floor(r / 2)), c))
    for i in range(int(np.floor(r / 2))):
        res[i, :] = (im[2 * i - 1, :] + im[2 * i, :]) / 2
    return res


def iter_difference_v(im: np.ndarray):
    r, c = im.shape[0], im.shape[1]
    res = np.zeros((int(np.floor(r / 2)), c))
    for i in range(int(np.floor(r / 2))):
        res[i, :] = (im[2 * i, :] - im[2 * i - 1, :]) / 2
    return res


def dwt(im: np.ndarray, n=1):
    for i in range(n):
        s = iter_average_h(im)
        d = iter_difference_h(im)
        ul = iter_average_v(s)
        ur = iter_average_v(d)
        ll = iter_difference_v(s)
        lr = iter_difference_v(d)
    return ul, ur, ll, lr


def test_passed(
    test_chunk: np.ndarray,
    template_chunk: np.ndarray,
    compression_ratio=3,
    binarization_threshold=10,
    allowed_difference=0.05,
):
    test_dwt, _, _, _ = dwt(test_chunk, n=compression_ratio)
    template_dwt, _, _, _ = dwt(template_chunk, n=compression_ratio)

    diff = np.abs(template_dwt - test_dwt)
    diff_bin = diff > binarization_threshold

    return (diff_bin.sum() / diff_bin.size) < allowed_difference


DOCUMENTATION = """
# DWT
## Introduction
Brief introduction....

## Parameters
- COMPRESSION_RATIO: int = 3. Specify how strong compression should be.
- BINARIZATION_THRESHOLD: int = 10. Specify how to get binary image after compression. May require testing to get this parametr right, generally should be greater than zero and located some where between 20 and 100.
- ALLOWED_DIFFERENCE: float = 0.05 [%/100]. How much difference after binarization is allowed.
"""


class Module(IModule):
    def process(
        self,
        environment: dict,
        test_image: np.ndarray,
        template_image: np.array,
        inspection_zone_list: List[IModule.InspectionZone],
    ) -> List[IModule.InspectionLog]:
        # Algorithm does not require preprocessing for whole image

        COMPRESSION_RATIO = int(environment["COMPRESSION_RATIO"])
        assert (
            COMPRESSION_RATIO > 0
        ), "Compression is required to be non zero positive integer"

        BINARIZATION_THRESHOLD = int(environment["BINARIZATION_THRESHOLD"])
        assert (
            BINARIZATION_THRESHOLD > 0
        ), "Binarization threshold is required to be non zero positive integer"

        ALLOWED_DIFFERENCE = float(environment["ALLOWED_DIFFERENCE"])
        assert 1 >= ALLOWED_DIFFERENCE >= 0, "Allowed threshold should be from 0 to 1."

        inspection_log_list = []
        for inspection_zone in inspection_zone_list:
            test_chunk = self.apply_inspection_zone(test_image, inspection_zone)
            template_chunk = self.apply_inspection_zone(template_image, inspection_zone)

            passed = test_passed(
                test_chunk,
                template_chunk,
                compression_ratio=COMPRESSION_RATIO,
                binarization_threshold=BINARIZATION_THRESHOLD,
                allowed_difference=ALLOWED_DIFFERENCE,
            )
            inspection_log = IModule.InspectionLog("Ok", passed)
            inspection_zone_list.append(inspection_log)
        return inspection_log_list
