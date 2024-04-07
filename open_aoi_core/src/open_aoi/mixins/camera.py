import numpy as np
from open_aoi.mixins import Mixin


class CameraControlMixin(Mixin):
    def test(self) -> bool:
        raise NotImplementedError()

    def start(self) -> bool:
        raise NotImplementedError()

    def stop(self) -> bool:
        raise NotImplementedError()

    def capture(self) -> np.ndarray:
        raise NotImplementedError()
