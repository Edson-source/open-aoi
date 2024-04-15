import numpy as np
from typing import List
from open_aoi_core.content.modules import IModule

DOCUMENTATION = "This is dummy module that does nothing"


class Module(IModule):
    def process(
        self,
        environment: dict,
        test_image: np.ndarray,
        template_image: np.array,
        control_zone_list: List[IModule.ControlZone],
    ) -> List[IModule.ControlLog]:
        return [IModule.ControlLog("Sample!", False) for cz in control_zone_list]


module = Module()
