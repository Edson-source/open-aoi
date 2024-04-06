import numpy as np
from open_aoi.mixins import Mixin


class CameraControlMixin(Mixin):
    def test(self) -> bool:
        raise NotImplemented()

    def start(self) -> bool:
        raise NotImplemented()

    def stop(self) -> bool:
        raise NotImplemented()

    def capture(self) -> np.ndarray:
        raise NotImplemented()
