import numpy as np
from typing import List
from open_aoi_core.content.modules import IModule


class Module(IModule):
    def process(
        self,
        environment: dict,
        test_image: np.ndarray,
        template_image: np.array,
        control_zone_list: List[IModule.ControlZone],
    ) -> List[IModule.ControlLog]:
        print("Hello AOI!")
        return []
