import numpy as np

from open_aoi.mixins import Mixin


class ImageManipulationMixin(Mixin):
    def inpaint(self, im: np.ndarray) -> np.ndarray:
        pass

    def crop(self, im: np.ndarray) -> np.ndarray:
        pass
